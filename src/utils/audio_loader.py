import subprocess
import numpy as np
import os
import json

def get_audio_info(file_path):
    """
    Returns (channels, sample_rate, duration) using ffprobe.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'a:0',
        '-show_entries', 'stream=channels,sample_rate,duration',
        '-of', 'json',
        file_path
    ]
    
    try:
        output = subprocess.check_output(cmd).decode('utf-8')
        data = json.loads(output)
        if not data.get('streams'):
            return 0, 0, 0.0
        stream = data['streams'][0]
        channels = int(stream.get('channels', 2))
        sample_rate = int(stream.get('sample_rate', 44100))
        duration = float(stream.get('duration', 0.0))
        return channels, sample_rate, duration
    except Exception as e:
        print(f"Error probing file {file_path}: {e}")
        return 0, 0, 0.0

def load_audio_file(file_path, target_sample_rate=44100):
    """
    Decodes audio file to float32 numpy array using ffmpeg.
    Resamples to target_sample_rate.
    Returns (audio_data, channels, sample_rate)
    """
    channels, src_sample_rate, duration = get_audio_info(file_path)
    if channels == 0:
        return None, 0, 0
        
    cmd = [
        'ffmpeg',
        '-v', 'error',
        '-i', file_path,
        '-f', 'f32le',
        '-acodec', 'pcm_f32le',
        '-ar', str(target_sample_rate),
        '-ac', str(channels),
        '-'
    ]
    
    try:
        raw_data = subprocess.check_output(cmd)
        audio_data = np.frombuffer(raw_data, dtype=np.float32)
        
        # Reshape: (frames, channels)
        if len(audio_data) % channels != 0:
             # Handle partial frames if any (shouldn't happen with f32le)
             padding = channels - (len(audio_data) % channels)
             audio_data = np.pad(audio_data, (0, padding))
             
        frames = len(audio_data) // channels
        audio_data = audio_data.reshape((frames, channels))
        
        return audio_data, channels, target_sample_rate
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        return None, 0, 0
