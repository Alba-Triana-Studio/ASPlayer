import time
from src.core.graph import Graph
from src.core.node_types import TriggerNode, SourceNode, ChannelNode
from src.core.audio_engine import AudioEngine

def test_audio_engine():
    print("Initializing Graph...")
    graph = Graph()
    
    # Create nodes
    trigger = TriggerNode()
    source = SourceNode() # Default sine 440Hz
    channel = ChannelNode()
    
    graph.add_node(trigger)
    graph.add_node(source)
    graph.add_node(channel)
    
    # Connect nodes
    print("Connecting nodes...")
    graph.add_connection(trigger.id, source.id)
    graph.add_connection(source.id, channel.id)
    
    # Initialize engine
    print("Initializing Audio Engine...")
    engine = AudioEngine()
    engine.set_graph(graph)
    
    # Play
    print("Starting playback (2 seconds)...")
    engine.start()
    time.sleep(2)
    engine.stop()
    print("Playback stopped.")

if __name__ == "__main__":
    test_audio_engine()
