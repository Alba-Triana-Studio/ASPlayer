import sounddevice as sd
import numpy as np
import threading
import time as time_module
from typing import Optional, Dict, Any, List
from src.core.graph import Graph
from src.core.node import NodeType
from src.core.node_types import SourceType
from src.utils.audio_loader import load_audio_file

class PlaybackContext:
    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self.node_states: Dict[str, Any] = {}
        self.start_time = 0.0
        self.current_frame = 0

    def get_state(self, node_id: str, default_factory=dict):
        if node_id not in self.node_states:
            self.node_states[node_id] = default_factory()
        return self.node_states[node_id]

class AudioEngine:
    def __init__(self):
        self.graph: Optional[Graph] = None
        self.is_playing = False
        self.stream: Optional[sd.OutputStream] = None
        self.sample_rate = 44100
        self.block_size = 8192 # Extremely safe block size for Pi Zero/3
        self.playback_context: Optional[PlaybackContext] = None
        self._lock = threading.Lock()
        
        # Property cache for thread safety and performance
        self._property_cache = {}
        self._property_queue = [] # Simple list as queue, protected by lock if needed, or just atomic appends
        self.on_play_state_change = None
        self._file_cache = {}

    def update_property(self, node_id, key, value):
        # Called from UI thread
        # We can push to a queue or update a shadow dict
        # Updating a shadow dict is thread-safe in Python for single items (atomic)
        # But let's use a specific method to be clean
        if not hasattr(self, '_property_cache'):
            self._property_cache = {}
            
        if node_id not in self._property_cache:
            self._property_cache[node_id] = {}
            
        self._property_cache[node_id][key] = value

    def get_node_property(self, node, key, default):
        # Called from Audio thread
        # Try to get from cache first
        if hasattr(self, '_property_cache') and node.id in self._property_cache:
            if key in self._property_cache[node.id]:
                return self._property_cache[node.id][key]
        
        # Fallback to direct node access (slower, potentially risky)
        return node.get_property(key, default)

    def set_graph(self, graph: Graph):
        with self._lock:
            self.graph = graph
            # Cache active connections to avoid traversing full graph in callback
            self._update_graph_cache()

    def _update_graph_cache(self):
        # Build a simplified structure for the audio thread
        # This should be called whenever the graph topology changes
        if not self.graph:
            self._cached_graph = None
            return

        cache = {
            'channels': [],
            'nodes': {}
        }
        
        # Pre-fetch nodes
        for node_id, node in self.graph.nodes.items():
            cache['nodes'][node_id] = node
            if node.type == NodeType.CHANNEL:
                # Find inputs for this channel
                inputs = []
                input_connections = [
                    c for c in self.graph.connections.values() 
                    if c.to_node_id == node.id
                ]
                for conn in input_connections:
                    source = self.graph.nodes.get(conn.from_node_id)
                    if source and source.type == NodeType.SOURCE:
                        # Find triggers for this source
                        triggers = []
                        source_input_conns = [
                            c for c in self.graph.connections.values() 
                            if c.to_node_id == source.id
                        ]
                        for sic in source_input_conns:
                            trigger = self.graph.nodes.get(sic.from_node_id)
                            if trigger and trigger.type == NodeType.TRIGGER:
                                triggers.append(trigger.id)
                        
                        inputs.append({
                            'source_id': source.id,
                            'triggers': triggers
                        })
                
                cache['channels'].append({
                    'id': node.id,
                    'inputs': inputs
                })
        
        self._cached_graph = cache

    # Call this from UI when graph changes (add/remove node/connection)
    def notify_graph_change(self):
        with self._lock:
            self._update_graph_cache()

    def get_available_devices(self):
        devices = []
        try:
            all_devices = sd.query_devices()
            for idx, dev in enumerate(all_devices):
                if dev['max_output_channels'] > 0:
                    # Filter out likely duplicates or non-physical devices if needed
                    # For now, just return all output devices
                    devices.append({
                        'index': idx,
                        'name': dev['name'],
                        'channels': dev['max_output_channels'],
                        'api': dev['hostapi']
                    })
        except Exception as e:
            print(f"Error listing devices: {e}")
        return devices

    def set_output_device(self, device_index):
        if self.is_playing:
            self.stop()
            self.start(device_index)
        else:
            # Just store it for next start
            self._pending_device_index = device_index

    def start(self, device_index=None):
        if self.is_playing:
            return
        
        try:
            self.playback_context = PlaybackContext(self.sample_rate)
            self.playback_context.start_time = time_module.time()
            self.playback_context.current_frame = 0
            
            # Identify active nodes and initialize states if needed
            if self.graph:
                for node in self.graph.nodes.values():
                    if node.type == NodeType.SOURCE:
                         # Initialize phase for wave sources
                         self.playback_context.get_state(node.id, lambda: {"phase": 0.0})

            # Use specified device or default
            device_idx = device_index
            if device_idx is None and hasattr(self, '_pending_device_index'):
                device_idx = self._pending_device_index

            channels = 2
            if device_idx is not None:
                dev_info = sd.query_devices(device_idx)
                channels = dev_info['max_output_channels']
            else:
                # Query default output device info for channel count
                device_info = self.get_default_output_device_info()
                channels = device_info.get('max_output_channels', 2)

            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=channels,
                device=device_idx,
                callback=self._audio_callback
            )
            self.stream.start()
            self.is_playing = True
            if self.on_play_state_change:
                self.on_play_state_change(True)
            print(f"Audio Engine Started (Device: {device_idx}, Channels: {channels})")
        except Exception as e:
            print(f"Error starting audio engine: {e}")
            self.is_playing = False
            if self.on_play_state_change:
                self.on_play_state_change(False)

    def stop(self):
        if not self.is_playing:
            return
            
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        self.is_playing = False
        if self.on_play_state_change:
            self.on_play_state_change(False)
        self.playback_context = None
        print("Audio Engine Stopped")

    def _audio_callback(self, outdata, frames, time, status):
        if status:
            print(status)
        
        # Initialize silence
        outdata.fill(0)
        
        # Use cached graph structure
        cached_graph = getattr(self, '_cached_graph', None)
        
        if not cached_graph or not self.playback_context:
            return

        # Per-block cache for source generation to handle shared sources
        # Key: source_node_id, Value: audio_chunk
        self._block_source_cache = {}

        channels = outdata.shape[1]
        # Buffer to accumulate audio for this block
        mixed_audio = np.zeros((frames, channels), dtype=np.float32)

        for channel_info in cached_graph['channels']:
            channel_node = cached_graph['nodes'].get(channel_info['id'])
            if not channel_node: continue
            
            for input_info in channel_info['inputs']:
                source_node = cached_graph['nodes'].get(input_info['source_id'])
                if source_node:
                    # Process source
                    audio_chunk = self._process_source_cached(source_node, input_info['triggers'], frames)
                    
                    # Apply channel mapping
                    channel_index = self.get_node_property(channel_node, "channel_index", 0)
                    volume = self.get_node_property(channel_node, "volume", 1.0)
                    source_channel_index = self.get_node_property(channel_node, "source_channel_index", 0)
                    
                    if channel_index > 0:
                        idx = channel_index - 1
                        if idx < channels:
                            # Mix to this channel
                            src_signal = audio_chunk
                            
                            # Handle source channel selection
                            if src_signal.shape[1] > 1:
                                if source_channel_index > 0:
                                     # Select specific channel (1-based index)
                                     src_idx = source_channel_index - 1
                                     if src_idx < src_signal.shape[1]:
                                         src_signal = src_signal[:, src_idx:src_idx+1]
                                     else:
                                         src_signal = np.zeros((frames, 1), dtype=np.float32)
                                else:
                                     # Mix down to mono
                                     src_signal = np.mean(src_signal, axis=1, keepdims=True)
                            
                            mixed_audio[:, idx] += src_signal[:, 0] * volume

        # Update playback position
        if self.playback_context:
            self.playback_context.current_frame += frames

        # Clip to prevent distortion
        np.clip(mixed_audio, -1.0, 1.0, out=mixed_audio)
        outdata[:] = mixed_audio

    def _load_file_data(self, file_path):
        if file_path in self._file_cache:
            return self._file_cache[file_path]
            
        # Load
        print(f"Loading audio file: {file_path}")
        data, channels, sr = load_audio_file(file_path, self.sample_rate)
        
        if data is not None:
            self._file_cache[file_path] = data
            return data
        return None

    def _process_source_cached(self, source_node, trigger_ids, frames):
        # Check block cache first
        if hasattr(self, '_block_source_cache') and source_node.id in self._block_source_cache:
            return self._block_source_cache[source_node.id]

        # Optimized process source that doesn't traverse graph
        is_triggered = False
        
        # Check triggers
        if trigger_ids:
             # Logic for trigger type. If any trigger is present, we consider it triggered for now
             # In future, check trigger state
             is_triggered = True
        
        result = np.zeros((frames, 1), dtype=np.float32)
        if is_triggered:
            source_type = self.get_node_property(source_node, "source_type", SourceType.WAVE)
            
            if source_type == SourceType.WAVE:
                result = self._generate_wave(source_node, frames)
            elif source_type == SourceType.FILE:
                file_path = self.get_node_property(source_node, "file_path", "")
                if file_path:
                    audio_data = self._load_file_data(file_path)
                    if audio_data is not None:
                        # Properties
                        start_time = self.get_node_property(source_node, "start_time", 0.0)
                        end_time = self.get_node_property(source_node, "end_time", 0.0)
                        loop = self.get_node_property(source_node, "loop", False)
                        
                        total_file_samples = len(audio_data)
                        start_offset = int(start_time * self.sample_rate)
                        end_offset = int(end_time * self.sample_rate)
                        
                        # Validate range
                        if start_offset < 0: start_offset = 0
                        if end_offset <= start_offset or end_offset > total_file_samples:
                            end_offset = total_file_samples
                            
                        play_len = end_offset - start_offset
                        
                        if play_len <= 0:
                             result = np.zeros((frames, audio_data.shape[1]), dtype=np.float32)
                        else:
                            # Calculate current position in the "playable window"
                            current_frame = self.playback_context.current_frame
                            
                            if loop:
                                relative_pos = current_frame % play_len
                            else:
                                relative_pos = current_frame
                                
                            # Map to file index
                            start_sample = start_offset + relative_pos
                            
                            if relative_pos < play_len:
                                # We have some samples to play
                                available = play_len - relative_pos
                                to_read = min(frames, available)
                                
                                result = np.zeros((frames, audio_data.shape[1]), dtype=np.float32)
                                
                                # Read main chunk
                                chunk = audio_data[start_sample : start_sample + to_read]
                                result[:to_read] = chunk
                                
                                # Handle loop wrapping within the block if needed
                                if to_read < frames and loop:
                                    remaining = frames - to_read
                                    # Wrap back to start_offset
                                    # This can be complex if loop_len < frames, but for simplicity:
                                    # Just fill from start
                                    # Recurse or loop? Simple fill for now (one wrap per block max assumption, but play_len could be small)
                                    # Better:
                                    filled = to_read
                                    while filled < frames:
                                        needed = frames - filled
                                        # Start from start_offset
                                        chunk_len = min(needed, play_len)
                                        result[filled : filled + chunk_len] = audio_data[start_offset : start_offset + chunk_len]
                                        filled += chunk_len
                            else:
                                # Past end, silence
                                result = np.zeros((frames, audio_data.shape[1]), dtype=np.float32)
        
        # Cache the result
        if hasattr(self, '_block_source_cache'):
            self._block_source_cache[source_node.id] = result
            
        return result

    def _process_source(self, source_node, frames):
        # Legacy method kept for compatibility if needed, but not used in optimized path
        return self._process_source_cached(source_node, [], frames)

    def _generate_wave(self, source_node, frames):
        state = self.playback_context.get_state(source_node.id, lambda: {"phase": 0.0})
        phase = state["phase"]
        
        # Use new get_node_property method
        try:
            frequency = float(self.get_node_property(source_node, "frequency", 440.0))
        except (ValueError, TypeError):
            frequency = 440.0
            
        wave_type = self.get_node_property(source_node, "wave_type", "sine")
        
        # Phase increment per sample
        phase_increment = frequency / self.sample_rate
        
        # Generate phase array
        phases = phase + np.arange(frames) * phase_increment
        
        if wave_type == "sine":
            audio = np.sin(2 * np.pi * phases)
        elif wave_type == "square":
            audio = np.sign(np.sin(2 * np.pi * phases))
        elif wave_type == "sawtooth":
            audio = 2 * (phases % 1) - 1
        else:
            audio = np.sin(2 * np.pi * phases)
            
        # Update state
        # Keep phase within [0, 1) to avoid overflow
        state["phase"] = (phase + frames * phase_increment) % 1.0
        
        return audio.reshape(-1, 1).astype(np.float32)

    def get_devices(self):
        return sd.query_devices()

    def get_default_output_device_info(self):
        try:
            return sd.query_devices(kind='output')
        except Exception as e:
            print(f"Error querying output device: {e}")
            return {"name": "Default", "max_output_channels": 2}
