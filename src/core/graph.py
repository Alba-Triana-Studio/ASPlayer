from typing import List, Dict, Any, Optional
from src.core.node import Node, NodeType
from src.core.connection import Connection
from src.core.node_types import TriggerNode, SourceNode, ChannelNode
import uuid

class Graph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.connections: Dict[str, Connection] = {}
        self.id = str(uuid.uuid4())
        self.label = "Workspace"
        self.settings: Dict[str, Any] = {} # Global settings for this graph (e.g. audio device)

    def add_node(self, node: Node):
        self.nodes[node.id] = node

    def remove_node(self, node_id: str):
        if node_id in self.nodes:
            # Remove all connections associated with this node
            connections_to_remove = []
            for conn_id, conn in self.connections.items():
                if conn.from_node_id == node_id or conn.to_node_id == node_id:
                    connections_to_remove.append(conn_id)
            
            for conn_id in connections_to_remove:
                self.remove_connection(conn_id)
            
            del self.nodes[node_id]

    def add_connection(self, from_node_id: str, to_node_id: str) -> Optional[Connection]:
        if from_node_id not in self.nodes or to_node_id not in self.nodes:
            return None
            
        from_node = self.nodes[from_node_id]
        to_node = self.nodes[to_node_id]

        # Validate connection logic
        # Trigger -> Source -> Channel
        if from_node.type == NodeType.TRIGGER and to_node.type != NodeType.SOURCE:
            return None
        if from_node.type == NodeType.SOURCE and to_node.type != NodeType.CHANNEL:
            return None
        if from_node.type == NodeType.CHANNEL:
             # Channel cannot be a source
            return None
        if to_node.type == NodeType.TRIGGER:
            # Trigger cannot be a target
            return None

        # Check for existing connection to avoid duplicates (optional, but good practice)
        for conn in self.connections.values():
            if conn.from_node_id == from_node_id and conn.to_node_id == to_node_id:
                return conn # Return existing connection

        connection = Connection(from_node_id, to_node_id)
        self.connections[connection.id] = connection
        
        from_node.add_output_connection(connection.id)
        to_node.add_input_connection(connection.id)
        
        return connection

    def remove_connection(self, connection_id: str):
        if connection_id in self.connections:
            conn = self.connections[connection_id]
            if conn.from_node_id in self.nodes:
                self.nodes[conn.from_node_id].remove_output_connection(connection_id)
            if conn.to_node_id in self.nodes:
                self.nodes[conn.to_node_id].remove_input_connection(connection_id)
            del self.connections[connection_id]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "settings": self.settings,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "connections": [conn.to_dict() for conn in self.connections.values()]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Graph':
        graph = cls()
        graph.id = data.get("id", str(uuid.uuid4()))
        graph.label = data.get("label", "Workspace")
        graph.settings = data.get("settings", {})
        
        # Recreate nodes
        for node_data in data.get("nodes", []):
            node_type_str = node_data.get("type")
            node = None
            if node_type_str == NodeType.TRIGGER.value:
                node = TriggerNode()
            elif node_type_str == NodeType.SOURCE.value:
                node = SourceNode()
            elif node_type_str == NodeType.CHANNEL.value:
                node = ChannelNode()
            
            if node:
                node.id = node_data.get("id")
                node.label = node_data.get("label")
                node.properties = node_data.get("properties", {})
                node.position = node_data.get("position", (0, 0))
                graph.add_node(node)
                
        # Recreate connections
        for conn_data in data.get("connections", []):
            from_id = conn_data.get("from_node_id")
            to_id = conn_data.get("to_node_id")
            if from_id and to_id:
                graph.add_connection(from_id, to_id)
                
        return graph
