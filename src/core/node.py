import uuid
from typing import List, Dict, Any, Optional
from enum import Enum

class NodeType(Enum):
    TRIGGER = "trigger"
    SOURCE = "source"
    CHANNEL = "channel"

class Node:
    def __init__(self, node_type: NodeType, label: str = "Node"):
        self.id = str(uuid.uuid4())
        self.type = node_type
        self.label = label
        self.properties: Dict[str, Any] = {}
        self.inputs: List[str] = []  # List of connection IDs connected to input
        self.outputs: List[str] = [] # List of connection IDs connected to output
        
        # Position in the UI (x, y) - to be updated by the UI layer
        self.position = (0, 0)

    def add_input_connection(self, connection_id: str):
        self.inputs.append(connection_id)

    def add_output_connection(self, connection_id: str):
        self.outputs.append(connection_id)

    def remove_input_connection(self, connection_id: str):
        if connection_id in self.inputs:
            self.inputs.remove(connection_id)

    def remove_output_connection(self, connection_id: str):
        if connection_id in self.outputs:
            self.outputs.remove(connection_id)

    def set_property(self, key: str, value: Any):
        self.properties[key] = value
        # Notify audio engine if possible, or use observer pattern
        # For now, we rely on the controller to update the engine cache
        # But we can add a hook here
        if hasattr(self, 'on_property_change'):
            self.on_property_change(self.id, key, value)

    def get_property(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "label": self.label,
            "properties": self.properties,
            "position": self.position
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Node':
        # This should be implemented by subclasses or a factory
        pass
