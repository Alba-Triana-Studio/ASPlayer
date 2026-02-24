import uuid
from typing import Dict, Any

class Connection:
    def __init__(self, from_node_id: str, to_node_id: str):
        self.id = str(uuid.uuid4())
        self.from_node_id = from_node_id
        self.to_node_id = to_node_id
        self.label = "Connection"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "label": self.label
        }
