import unittest
import os
import json
from src.core.graph import Graph
from src.core.node_types import TriggerNode, SourceNode, ChannelNode
from src.core.persistence import PersistenceManager

class TestPersistence(unittest.TestCase):
    def setUp(self):
        self.test_file = "test_workspace.json"
        self.graph = Graph()
        
        # Create a simple graph
        self.t = TriggerNode()
        self.t.position = (10, 10)
        self.s = SourceNode()
        self.s.set_property("frequency", 880)
        self.s.position = (20, 20)
        self.c = ChannelNode()
        self.c.position = (30, 30)
        
        self.graph.add_node(self.t)
        self.graph.add_node(self.s)
        self.graph.add_node(self.c)
        
        self.graph.add_connection(self.t.id, self.s.id)
        self.graph.add_connection(self.s.id, self.c.id)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_save_and_load(self):
        # Save
        success = PersistenceManager.save_workspace(self.graph, self.test_file)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.test_file))
        
        # Load
        loaded_graph = PersistenceManager.load_workspace(self.test_file)
        self.assertIsNotNone(loaded_graph)
        
        # Verify Nodes
        self.assertEqual(len(loaded_graph.nodes), 3)
        self.assertTrue(self.t.id in loaded_graph.nodes)
        self.assertTrue(self.s.id in loaded_graph.nodes)
        
        # Verify Properties
        loaded_source = loaded_graph.nodes[self.s.id]
        self.assertEqual(loaded_source.get_property("frequency"), 880)
        self.assertEqual(loaded_source.position, [20, 20]) # JSON might convert tuple to list
        
        # Verify Connections
        self.assertEqual(len(loaded_graph.connections), 2)

if __name__ == '__main__':
    unittest.main()
