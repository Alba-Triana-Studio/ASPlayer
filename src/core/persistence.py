import json
import os
from typing import Dict, Any, Optional
from src.core.graph import Graph

class PersistenceManager:
    @staticmethod
    def save_workspace(graph: Graph, file_path: str):
        data = graph.to_dict()
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving workspace: {e}")
            return False

    @staticmethod
    def load_workspace(file_path: str) -> Optional[Graph]:
        if not os.path.exists(file_path):
            return None
            
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return Graph.from_dict(data)
        except Exception as e:
            print(f"Error loading workspace: {e}")
            return None
