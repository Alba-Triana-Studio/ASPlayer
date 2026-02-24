from src.core.graph import Graph
from src.core.audio_engine import AudioEngine
from src.core.node_types import TriggerNode, SourceNode, ChannelNode
from src.core.node import NodeType
from src.core.persistence import PersistenceManager
from src.core.config_manager import ConfigManager
from src.ui.popups import SaveDialog, LoadDialog
from src.ui.connection_widget import ConnectionWidget
from kivy.uix.popup import Popup
from kivy.graphics import Color, Line, Bezier
from kivy.uix.widget import Widget
import os

class Controller:
    def __init__(self):
        self.graph = Graph()
        self.audio_engine = AudioEngine()
        self.audio_engine.set_graph(self.graph)
        self.ui_root = None # Reference to MainLayout
        self.current_workspace_file = "workspace.json"
        
        self.config_manager = ConfigManager()

        # Connection Dragging State
        self.dragging_connection = False
        self.drag_start_node = None
        self.drag_start_pin_is_input = False
        self.drag_current_pos = (0, 0)
        
        # Initial Graph Loading
        last_file = self.config_manager.get_last_opened_file()
        if last_file and os.path.exists(last_file):
            print(f"Loading last opened file: {last_file}")
            self.current_workspace_file = last_file
            loaded_graph = PersistenceManager.load_workspace(last_file)
            if loaded_graph:
                self.graph = loaded_graph
                self.audio_engine.set_graph(self.graph)
            else:
                self._create_initial_graph()
        else:
            self._create_initial_graph()

    def _create_initial_graph(self):
        self.graph = Graph()
        self.audio_engine.set_graph(self.graph)
        
        # Start with just one output channel as per spec (minimalist start)
        c = ChannelNode(label="Output 1")
        c.position = (350, 150) # Adjusted for 480x320 screen
        c.set_property("channel_index", 1) # Default map to Channel 1
        
        # Hook up property change notification
        c.on_property_change = self.audio_engine.update_property
        
        self.graph.add_node(c)

    def set_ui(self, ui_root):
        self.ui_root = ui_root
        # Bind UI events
        self.ui_root.bottom_bar.play_btn.bind(on_release=self.toggle_play)
        
        # Monitor audio engine state to update play button
        # We can't bind directly to is_playing as it's not a Kivy property
        # So we'll use a Clock interval to check or add a callback in AudioEngine
        # For now, let's add a simple callback hook to AudioEngine
        self.audio_engine.on_play_state_change = self._on_play_state_change
        
        # Check for OPEN triggers
        self._check_auto_start_triggers()
        
        # Bind Left Panel Buttons
        if hasattr(self.ui_root.left_panel, 'save_btn'):
            self.ui_root.left_panel.save_btn.bind(on_release=self.save_workspace)
        if hasattr(self.ui_root.left_panel, 'load_btn'):
            self.ui_root.left_panel.load_btn.bind(on_release=self.load_workspace)
        if hasattr(self.ui_root.left_panel, 'clear_btn'):
            self.ui_root.left_panel.clear_btn.bind(on_release=self.clear_workspace)
            
        if hasattr(self.ui_root.left_panel, 'channel_spinner'):
            self.ui_root.left_panel.channel_spinner.bind(text=self.on_channel_count_change)

        # Initialize UI with current graph state
        # Get Device Info
        device_info = self.audio_engine.get_default_output_device_info()
        if hasattr(self.ui_root.left_panel, 'set_device_info'):
            self.ui_root.left_panel.set_device_info(device_info)
            
        # Get Available Devices for Selector
        devices = self.audio_engine.get_available_devices()
        if hasattr(self.ui_root.left_panel, 'set_device_list'):
            self.ui_root.left_panel.set_device_list(devices)
            
        if hasattr(self.ui_root.left_panel, 'device_spinner'):
            self.ui_root.left_panel.device_spinner.bind(text=self.on_device_select)
            
            # Restore visual selection if graph has settings and audio_device is saved
            if self.graph and 'audio_device' in self.graph.settings:
                saved_device_name = self.graph.settings['audio_device']
                # Find matching spinner value
                # Spinner values format: "Name (Index)" or truncated "Name... (Index)"
                # We need to find the one that corresponds to the device index we want, 
                # or match by name if possible.
                
                # First, find the index of the device by name from current available devices
                target_index = -1
                for dev in devices:
                    if dev['name'] == saved_device_name:
                        target_index = dev['index']
                        break
                
                if target_index != -1:
                    # Set the audio engine device (ensure it's set)
                    self.audio_engine.set_output_device(target_index)
                    
                    # Find the spinner string that contains this index "({index})"
                    suffix = f"({target_index})"
                    for val in self.ui_root.left_panel.device_spinner.values:
                        if val.endswith(suffix):
                            # This will trigger on_device_select, which is fine, it will re-confirm settings
                            self.ui_root.left_panel.device_spinner.text = val
                            break

        # Restore channel count spinner
        if hasattr(self.ui_root.left_panel, 'channel_spinner'):
            channels = [n for n in self.graph.nodes.values() if n.type == NodeType.CHANNEL]
            if channels:
                self.ui_root.left_panel.channel_spinner.text = str(len(channels))

        self.refresh_ui()

    def _check_auto_start_triggers(self):
        # Look for Triggers with type 'open' and fire them
        if not self.graph:
            return
            
        should_start = False
        for node in self.graph.nodes.values():
            if node.type == NodeType.TRIGGER:
                trigger_type = node.get_property("trigger_type", "on_start")
                if trigger_type == "open":
                    should_start = True
                    break
        
        if should_start:
            print("Auto-starting due to 'open' trigger")
            # Defer slightly to ensure audio engine is fully ready
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.audio_engine.start(), 0.1)

    def on_device_select(self, spinner, text):
        # Parse "Name (Index)"
        try:
            # Extract index from last parentheses
            idx_str = text.split('(')[-1].replace(')', '')
            device_index = int(idx_str)
            print(f"Switching to device index: {device_index}")
            self.audio_engine.set_output_device(device_index)
            
            # Update device info label
            all_devices = self.audio_engine.get_devices()
            dev_info = all_devices[device_index]
            
            # Save to graph settings
            if isinstance(dev_info, dict):
                 self.graph.settings['audio_device'] = dev_info['name']
            else:
                 self.graph.settings['audio_device'] = dev_info['name']

            # Convert to dict format expected by UI if it's not already
            if not isinstance(dev_info, dict):
                # It might be a struct from sounddevice
                dev_info = {
                    'name': dev_info['name'],
                    'max_output_channels': dev_info['max_output_channels']
                }
            self.ui_root.left_panel.set_device_info(dev_info)
            
        except Exception as e:
            print(f"Error switching device: {e}")

    def _on_play_state_change(self, is_playing):
        # Update UI button state from non-UI thread potentially
        # So we should use Clock.schedule_once
        from kivy.clock import Clock
        def update_btn(dt):
            if self.ui_root:
                self.ui_root.bottom_bar.play_btn.text = "STOP" if is_playing else "PLAY"
        Clock.schedule_once(update_btn)

    def toggle_play(self, instance):
        if self.audio_engine.is_playing:
            self.audio_engine.stop()
            instance.text = "PLAY"
        else:
            self.audio_engine.start()
            instance.text = "STOP"
            
    def save_workspace(self, instance):
        content = SaveDialog(save_callback=self._do_save, cancel_callback=self._dismiss_popup, default_filename=os.path.basename(self.current_workspace_file))
        self._popup = Popup(title="Save Workspace", content=content, size_hint=(0.9, 0.9))
        self._popup.open()

    def _do_save(self, path, filename):
        full_path = os.path.join(path, filename)
        if PersistenceManager.save_workspace(self.graph, full_path):
            print(f"Workspace saved to {full_path}")
            self.current_workspace_file = full_path
            self.config_manager.set_last_opened_file(full_path)
        self._dismiss_popup()

    def load_workspace(self, instance):
        content = LoadDialog(load_callback=self._do_load, cancel_callback=self._dismiss_popup)
        self._popup = Popup(title="Load Workspace", content=content, size_hint=(0.9, 0.9))
        self._popup.open()

    def _do_load(self, file_path):
        if not os.path.exists(file_path):
            return
            
        loaded_graph = PersistenceManager.load_workspace(file_path)
        if loaded_graph:
            self.graph = loaded_graph
            
            # Restore audio device if saved
            device_name = self.graph.settings.get('audio_device')
            if device_name:
                devices = self.audio_engine.get_available_devices()
                found_index = None
                for dev in devices:
                    if dev['name'] == device_name:
                        found_index = dev['index']
                        break
                
                if found_index is not None:
                    print(f"Restoring audio device: {device_name} (Index: {found_index})")
                    self.audio_engine.set_output_device(found_index)
                    # Update spinner if UI is ready
                    if self.ui_root and hasattr(self.ui_root.left_panel, 'device_spinner'):
                        suffix = f"({found_index})"
                        for val in self.ui_root.left_panel.device_spinner.values:
                            if val.endswith(suffix):
                                self.ui_root.left_panel.device_spinner.text = val
                                break
            
            # Sync Channel Spinner
            channels = [n for n in self.graph.nodes.values() if n.type == NodeType.CHANNEL]
            if self.ui_root and hasattr(self.ui_root.left_panel, 'channel_spinner'):
                self.ui_root.left_panel.channel_spinner.text = str(len(channels))

            # Reconnect property change callbacks for all nodes
            for node in self.graph.nodes.values():
                node.on_property_change = self.audio_engine.update_property
                # Pre-populate audio engine cache
                for key, val in node.properties.items():
                    self.audio_engine.update_property(node.id, key, val)

            self.audio_engine.set_graph(self.graph)
            self.refresh_ui()
            self.current_workspace_file = file_path
            self.config_manager.set_last_opened_file(file_path)
            print(f"Workspace loaded from {file_path}")
        self._dismiss_popup()

    def _dismiss_popup(self):
        if hasattr(self, '_popup') and self._popup:
            self._popup.dismiss()

    def clear_workspace(self, instance):
        self._create_initial_graph()
        self.refresh_ui()
        print("Workspace cleared")

    def on_channel_count_change(self, spinner, text):
        try:
            target_count = int(text)
            self.set_channel_count(target_count)
        except ValueError:
            pass

    def set_channel_count(self, count):
        # Find existing channel nodes
        channels = [n for n in self.graph.nodes.values() if n.type == NodeType.CHANNEL]
        # Sort by label number to keep order stable
        channels.sort(key=lambda n: int(n.label.split()[-1]) if n.label.split()[-1].isdigit() else 0)
        
        current_count = len(channels)
        
        if count > current_count:
            # Add new channels
            for i in range(current_count, count):
                c = ChannelNode(label=f"Output {i+1}")
                c.set_property("channel_index", i+1) # Default map to corresponding channel
                c.on_property_change = self.audio_engine.update_property
                self.graph.add_node(c)
                channels.append(c)
        elif count < current_count:
            # Remove channels (from bottom/last added)
            to_remove = channels[count:] # The ones to remove
            for node in to_remove:
                self._remove_node_safe(node)
            channels = channels[:count]
        
        # Reposition ALL channels to ensure clean layout
        start_y = 250
        gap = 60
        for i, node in enumerate(channels):
            node.position = (350, start_y - (i * gap))
                
        self.audio_engine.notify_graph_change()
        self.refresh_ui()

    def _remove_node_safe(self, node):
        # Helper to remove node and its connections
        # Remove connections first
        to_remove_conns = []
        for conn_id, conn in self.graph.connections.items():
            if conn.from_node_id == node.id or conn.to_node_id == node.id:
                to_remove_conns.append(conn_id)
        
        for conn_id in to_remove_conns:
            self.graph.remove_connection(conn_id)
            
        self.graph.remove_node(node.id)

    def handle_pin_click(self, node, is_input):
        # This is now handled by drag and drop, but we keep it for backward compatibility or direct clicks
        # If input pin clicked on Channel, create Source (Backward Flow) - ONLY IF NOT CONNECTED
        if is_input and node.type == NodeType.CHANNEL:
            # Check if already connected
            is_connected = False
            for conn in self.graph.connections.values():
                if conn.to_node_id == node.id:
                    is_connected = True
                    break
            
            if is_connected:
                print("Channel already has a source connected")
                return

            # Create Source connected to this Channel
            new_node = SourceNode()
            # Position to the left of the channel
            new_node.position = (node.position[0] - 150, node.position[1])
            if new_node.position[0] < 10: new_node.position = (10, node.position[1])
            
            self.graph.add_node(new_node)
            self.graph.add_connection(new_node.id, node.id)
            self.audio_engine.notify_graph_change()
            self.refresh_ui()
            
        elif is_input and node.type == NodeType.SOURCE:
             # Create Trigger connected to this Source
            new_node = TriggerNode()
            # Position to the left of the source
            new_node.position = (node.position[0] - 150, node.position[1])
            if new_node.position[0] < 10: new_node.position = (10, node.position[1])
            
            self.graph.add_node(new_node)
            self.graph.add_connection(new_node.id, node.id)
            self.audio_engine.notify_graph_change()
            self.refresh_ui()

    def start_connection_drag(self, node, is_input):
        self.dragging_connection = True
        self.drag_start_node = node
        self.drag_start_pin_is_input = is_input
        print(f"Started drag from {node.label} ({'Input' if is_input else 'Output'})")

    def update_connection_drag(self, pos):
        if self.dragging_connection:
            self.drag_current_pos = pos
            # Ideally redraw a temporary line here
            self.update_connections_view()

    def end_connection_drag(self, end_node, is_input):
        if not self.dragging_connection:
            return
            
        start_node = self.drag_start_node
        start_is_input = self.drag_start_pin_is_input
        
        self.dragging_connection = False
        self.drag_start_node = None
        
        if not end_node:
            self.update_connections_view() # Clear temp line
            return
            
        # Validate connection
        # Must connect Output -> Input
        from_node = None
        to_node = None
        
        if not start_is_input and is_input:
            from_node = start_node
            to_node = end_node
        elif start_is_input and not is_input:
            from_node = end_node
            to_node = start_node
        else:
            print("Invalid connection: Must connect Output to Input")
            self.update_connections_view()
            return
            
        if from_node.id == to_node.id:
            print("Cannot connect node to itself")
            self.update_connections_view()
            return

        # Check Channel Constraints: Channel can only have 1 input
        if to_node.type == NodeType.CHANNEL:
            for conn in self.graph.connections.values():
                if conn.to_node_id == to_node.id:
                    print("Channel already connected")
                    self.update_connections_view()
                    return

        # Create Connection
        self.graph.add_connection(from_node.id, to_node.id)
        self.audio_engine.notify_graph_change()
        self.refresh_ui()
        print(f"Connected {from_node.label} to {to_node.label}")

    def select_node(self, node):
        print(f"Selected node: {node.label}")
        if self.ui_root:
            # Open Right Panel
            self.ui_root.right_panel.is_open = True
            # Update Content
            self.ui_root.right_panel.update_inspector(node, self.graph)

    def add_node(self, node):
        # Center node on screen initially or use default
        if node.position == (0, 0):
            node.position = (self.ui_root.node_canvas.width / 2, self.ui_root.node_canvas.height / 2)
            
        # Hook up property change notification
        node.on_property_change = self.audio_engine.update_property
        
        self.graph.add_node(node)
        self.audio_engine.notify_graph_change()
        self.refresh_ui()

    def remove_node(self, node):
        self.graph.remove_node(node.id)
        self.audio_engine.notify_graph_change()
        self.refresh_ui()
        # If inspector was showing this node, clear it
        self.ui_root.right_panel.update_inspector(None)

    def add_connection(self, from_node, to_node):
        # Validate connection
        # Only Source -> Channel or Trigger -> Source
        valid = False
        if from_node.type == NodeType.TRIGGER and to_node.type == NodeType.SOURCE:
            valid = True
        elif from_node.type == NodeType.SOURCE and to_node.type == NodeType.CHANNEL:
            valid = True
            
        if valid:
            self.graph.add_connection(from_node.id, to_node.id)
            self.audio_engine.notify_graph_change()
            self.refresh_ui()
        else:
            print("Invalid connection type")

    def remove_connection(self, connection_id):
        self.graph.remove_connection(connection_id)
        self.audio_engine.notify_graph_change()
        self.refresh_ui()

    def update_connections_view(self):
        # Efficiently redraw connections without full refresh
        if not self.ui_root: return
        canvas = self.ui_root.node_canvas
        
        # We only need to draw the temporary drag line here
        # Existing connections update themselves via bindings in ConnectionWidget
        self._draw_drag_line(canvas)

    def refresh_ui(self):
        if not self.ui_root:
            return
            
        canvas = self.ui_root.node_canvas
        canvas.clear_widgets()
        
        self.node_widgets_map = {}
        
        # 1. Create Node Widgets first (to get references) but don't add to canvas yet
        # We want connections BEHIND nodes.
        nodes_to_add = []
        for node in self.graph.nodes.values():
            widget = canvas.add_node_widget(node)
            # This implementation of add_node_widget likely adds it to the canvas.
            # We remove it to re-add later in correct order (on top of connections)
            canvas.remove_widget(widget) 
            
            # Pass controller reference to widget
            widget.controller = self
            self.node_widgets_map[node.id] = widget
            nodes_to_add.append(widget)
            
        # 2. Create and Add Connection Widgets
        for conn_id, conn in self.graph.connections.items():
            from_widget = self.node_widgets_map.get(conn.from_node_id)
            to_widget = self.node_widgets_map.get(conn.to_node_id)
            
            if from_widget and to_widget:
                conn_widget = ConnectionWidget(
                    connection_id=conn_id,
                    source_widget=from_widget,
                    target_widget=to_widget,
                    controller=self
                )
                canvas.add_widget(conn_widget)
        
        # 3. Add Node Widgets (so they are on top)
        for widget in nodes_to_add:
            canvas.add_widget(widget)
            
        # 4. Draw drag line if needed (rare case on refresh, but good practice)
        self._draw_drag_line(canvas)

    def _draw_connections(self, canvas_layout):
        # DEPRECATED: Replaced by ConnectionWidget and _draw_drag_line
        self._draw_drag_line(canvas_layout)

    def _draw_drag_line(self, canvas_layout):
        # Draw temporary connection line while dragging
        canvas_layout.canvas.after.remove_group('drag_connection')
        
        if self.dragging_connection and self.drag_start_node:
            start_widget = self.node_widgets_map.get(self.drag_start_node.id)
            if not start_widget: return
            
            with canvas_layout.canvas.after:
                Color(0.5, 0.5, 0.5, 1, group='drag_connection') # Grey for temp line
                
                # Calculate start point
                if self.drag_start_pin_is_input:
                    # Dragging from Input Pin -> Output (Reverse)
                    x1, y1 = start_widget.x, start_widget.center_y
                else:
                    # Dragging from Output Pin -> Input (Normal)
                    x1, y1 = start_widget.right, start_widget.center_y
                
                x2, y2 = self.drag_current_pos
                
                # Draw Bezier Curve for drag preview
                cx1 = x1 + 50 if not self.drag_start_pin_is_input else x1 - 50
                cy1 = y1
                cx2 = x2 - 50 if not self.drag_start_pin_is_input else x2 + 50
                cy2 = y2
                
                # If dragging from Input, we are looking for an Output, so curve should enter from right
                # If dragging from Output, we are looking for an Input, so curve should enter from left
                
                # Simple S-curve to cursor
                Bezier(points=[x1, y1, cx1, cy1, cx2, cy2, x2, y2], width=1.5, group='drag_connection')
