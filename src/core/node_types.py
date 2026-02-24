from typing import List, Dict, Any, Optional
from src.core.node import Node, NodeType

class TriggerNode(Node):
    def __init__(self, label: str = "Trigger"):
        super().__init__(NodeType.TRIGGER, label)
        # Default properties
        self.properties = {
            "trigger_type": "on_start",
            "manual_trigger": False
        }

class SourceType(str):
    WAVE = "wave"
    FILE = "file"

class SourceNode(Node):
    def __init__(self, source_type: str = SourceType.WAVE, label: str = "Source"):
        super().__init__(NodeType.SOURCE, label)
        self.source_type = source_type
        # Default properties
        self.properties = {
            "source_type": source_type,
            # Wave specific
            "wave_type": "sine",
            "frequency": 440,
            "duration_mode": "infinite", # infinite, default, intermittent
            "duration": 1.0, # seconds
            "interval": 1.0, # seconds for intermittent
            # File specific
            "file_path": "",
            "channels": 0,
            "sample_rate": 0,
            "file_duration": 0.0,
            "start_time": 0.0,
            "end_time": 0.0,
            "loop": False,
            "loop_count": 0, # 0 for infinite
            "padding_before": 0.0,
            "padding_after": 0.0
        }
    
    def set_source_type(self, source_type: str):
        self.source_type = source_type
        self.properties["source_type"] = source_type

class ChannelNode(Node):
    def __init__(self, label: str = "Output"):
        super().__init__(NodeType.CHANNEL, label)
        # Default properties
        self.properties = {
            "hardware_device": "default",
            "channel_mapping": "stereo", # left, right, stereo
            "source_channel_index": 0, # 0=Mix/All, 1=Ch1, 2=Ch2...
            "volume": 1.0
        }
