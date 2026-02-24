from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stencilview import StencilView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, Rectangle, Line
from kivy.properties import ObjectProperty, BooleanProperty, NumericProperty
from kivy.animation import Animation
from src.ui.node_widget import NodeWidget
from src.core.node import NodeType
from kivy.clock import Clock
import os
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from src.utils.audio_loader import get_audio_info
import math

def format_time(seconds):
    if not isinstance(seconds, (int, float)):
        return "00:00:00"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

class NumericKeypadPopup(BoxLayout):
    def __init__(self, callback, initial_value="", **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.callback = callback
        self.current_value = str(initial_value)
        
        # Display
        self.display = Label(text=self.current_value, size_hint_y=None, height=50, font_size='24sp', color=(1,1,1,1))
        with self.canvas.before:
            Color(0.2, 0.2, 0.2, 1)
            Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_rect)
        
        self.add_widget(self.display)
        
        # Grid
        grid = GridLayout(cols=3, spacing=5)
        self.add_widget(grid)
        
        keys = [
            '1', '2', '3',
            '4', '5', '6',
            '7', '8', '9',
            '.', '0', '<'
        ]
        
        for key in keys:
            btn = Button(text=key, font_size='20sp')
            btn.bind(on_release=self.on_key_press)
            grid.add_widget(btn)
            
        # Actions
        actions = BoxLayout(size_hint_y=None, height=50, spacing=5)
        cancel_btn = Button(text="Cancel", background_color=(0.8, 0.2, 0.2, 1))
        cancel_btn.bind(on_release=self.cancel)
        ok_btn = Button(text="OK", background_color=(0.2, 0.8, 0.2, 1))
        ok_btn.bind(on_release=self.confirm)
        
        actions.add_widget(cancel_btn)
        actions.add_widget(ok_btn)
        self.add_widget(actions)
        
        # Popup wrapper
        from kivy.uix.popup import Popup
        self.popup = Popup(title="Enter Value", content=self, size_hint=(0.8, 0.8))

    def _update_bg(self, instance, value):
        pass # Bg handled by parent popup mostly, but good to have local if needed
        
    def _update_rect(self, instance, value):
        # self.bg_rect.pos = instance.pos
        # self.bg_rect.size = instance.size
        pass

    def open(self):
        self.popup.open()
        
    def cancel(self, instance):
        self.popup.dismiss()
        
    def confirm(self, instance):
        if self.callback:
            self.callback(self.current_value)
        self.popup.dismiss()
        
    def on_key_press(self, instance):
        key = instance.text
        if key == '<':
            self.current_value = self.current_value[:-1]
        elif key == '.':
            if '.' not in self.current_value:
                self.current_value += key
        else:
            if self.current_value == "0" and key != '.':
                self.current_value = key
            else:
                self.current_value += key
        self.display.text = self.current_value

class NodeCanvas(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.95, 0.95, 0.95, 1) # Light gray background
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
    
    def add_node_widget(self, node):
        widget = NodeWidget(node=node)
        self.add_widget(widget)
        return widget

    def on_touch_down(self, touch):
        # Let children (nodes) handle it first
        if super().on_touch_down(touch):
            return True
            
        # If no child handled it, and we are touching the canvas
        if self.collide_point(*touch.pos):
            # Check if right panel is open
            main_layout = self.parent
            if main_layout and hasattr(main_layout, 'right_panel'):
                if main_layout.right_panel.is_open:
                    main_layout.right_panel.is_open = False
                    main_layout.right_panel._animate_position()
                    return True
        return False

class BottomBar(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 60
        self.padding = 10
        self.spacing = 10
        
        with self.canvas.before:
            Color(0.9, 0.9, 0.9, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

        # Play/Stop Button
        self.play_btn = Button(text="PLAY", size_hint_x=None, width=100)
        self.add_widget(self.play_btn)
        
        # Spacer
        self.add_widget(Label())

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

class SidePanel(FloatLayout):
    is_open = BooleanProperty(False)
    
    def __init__(self, side='left', **kwargs):
        super().__init__(**kwargs)
        self.side = side
        self.size_hint_x = None
        self.width = 180 # Panel Width
        self.size_hint_y = 1
        
        # Background (The main panel body)
        with self.canvas.before:
            Color(0.85, 0.85, 0.85, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)
        
        # ScrollView for content
        self.scroll_view = ScrollView(
            pos_hint={'x': 0, 'y': 0}, 
            size_hint=(1, 1),
            do_scroll_x=False, 
            do_scroll_y=True,
            bar_width=25, # Wider bars for touch
            scroll_type=['bars', 'content'], # Allow dragging content AND using bars
            bar_inactive_color=[0.7, 0.7, 0.7, 0.5], # Make bar visible even when inactive
        )
        self.add_widget(self.scroll_view)

        # Actual Content Layout (inside ScrollView) - GridLayout behaves better than BoxLayout for scrolling
        self.content_area = GridLayout(cols=1, spacing=10, padding=(0, 10, 0, 10), size_hint_y=None)
        self.content_area.bind(minimum_height=self.content_area.setter('height'))
        
        self.scroll_view.add_widget(self.content_area)
        
        # Toggle Handle (Arrow) - Outside the panel body effectively
        self.handle = Button(size_hint=(None, None), size=(40, 40))
        self.handle.bind(on_release=self.toggle)
        self.add_widget(self.handle)
        
        # Specific controls for Left Panel
        if self.side == 'left':
            self.setup_left_panel()
        
        self.bind(pos=self._update_handle_pos, size=self._update_handle_pos)

    def _update_handle_pos(self, *args):
        # Position handle relative to the panel
        if self.side == 'left':
            # Handle sticks out to the right
            self.handle.x = self.x + self.width
            self.handle.center_y = self.center_y
            self.handle.text = "<" if self.is_open else ">"
        else:
            # Handle sticks out to the left
            self.handle.right = self.x
            self.handle.center_y = self.center_y
            self.handle.text = ">" if self.is_open else "<"


    def set_device_info(self, info):
        if self.side != 'left':
            return
            
        name = info.get('name', 'Unknown')
        channels = info.get('max_output_channels', 2)
        
        text = f"Device: {name}\nMax Channels: {channels}"
        
        if hasattr(self, 'device_label'):
             self.device_label.text = text

    def set_device_list(self, devices):
        if self.side != 'left':
            return
            
        self.device_list = devices
        
        # Format for spinner: "Name (Index)"
        # Shorten name if too long
        values = []
        for d in devices:
            name = d['name']
            if len(name) > 20:
                name = name[:17] + "..."
            values.append(f"{name} ({d['index']})")
        
        if not hasattr(self, 'device_spinner'):
            self.content_area.add_widget(Label(text="Output Device:", size_hint_y=None, height=30, color=(0,0,0,1)))
            self.device_spinner = Spinner(
                text="Select Device",
                values=values,
                size_hint_y=None, height=40
            )
            # Bind in controller
            self.content_area.add_widget(self.device_spinner)
        else:
            self.device_spinner.values = values

    def setup_left_panel(self):
        self.save_btn = Button(text="SAVE", size_hint_y=None, height=40)
        self.content_area.add_widget(self.save_btn)
        
        self.load_btn = Button(text="LOAD", size_hint_y=None, height=40)
        self.content_area.add_widget(self.load_btn)

        self.clear_btn = Button(text="CLEAR", size_hint_y=None, height=40)
        self.content_area.add_widget(self.clear_btn)
        
        # Device Info
        self.device_label = Label(text="Device Info...", size_hint_y=None, height=40, color=(0,0,0,1))
        self.content_area.add_widget(self.device_label)
        
        # Channel Count Selector
        self.content_area.add_widget(Label(text="Channels:", size_hint_y=None, height=30, color=(0,0,0,1)))
        self.channel_spinner = Spinner(
            text="1",
            values=[str(i) for i in range(1, 9)],
            size_hint_y=None, height=40
        )
        self.content_area.add_widget(self.channel_spinner)

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def toggle(self, *args):
        self.is_open = not self.is_open
        self._animate_position()

    def _animate_position(self):
        if not self.parent:
            return
            
        target_x = 0
        if self.is_open:
            if self.side == 'left':
                target_x = 0
            else:
                target_x = self.parent.width - self.width
        else:
            if self.side == 'left':
                target_x = -self.width # Completely hidden
            else:
                target_x = self.parent.width # Completely hidden
                
        anim = Animation(x=target_x, duration=0.3, t='out_quad')
        anim.start(self)

    def on_touch_down(self, touch):
        # Allow handle to work even if panel is closed (handle is outside the main rect)
        if self.handle.collide_point(*touch.pos):
            self.toggle()
            return True
            
        if not self.collide_point(*touch.pos):
            return False
            
        if super().on_touch_down(touch):
            return True
            
        # If closed and touched background, toggle open
        if not self.is_open:
            self.toggle()
            return True
            
        return True

    def on_is_open(self, instance, value):
        self._animate_position()

    def on_size(self, *args):
        self._update_position()

    def _update_position(self):
        if not self.parent:
            return
            
        if self.is_open:
            if self.side == 'left':
                self.x = 0
            else:
                self.x = self.parent.width - self.width
        else:
            if self.side == 'left':
                self.x = -self.width # Completely hidden
            else:
                self.x = self.parent.width # Completely hidden

    def update_inspector(self, node, graph=None):
        if self.side != 'right':
            return
            
        self.content_area.clear_widgets()
        
        if not node:
            self.content_area.add_widget(Label(text="No Selection", color=(0,0,0,1)))
            return
            
        self.content_area.add_widget(Label(text=f"Type: {node.type.value.upper()}", size_hint_y=None, height=30, color=(0,0,0,1)))
        
        if node.type == NodeType.SOURCE:
            self._build_source_inspector(node)
        elif node.type == NodeType.CHANNEL:
            self._build_channel_inspector(node, graph)
        elif node.type == NodeType.TRIGGER:
            self._build_trigger_inspector(node)

    def _build_source_inspector(self, node):
        # Source Type Selector (Wave vs File)
        self.content_area.add_widget(Label(text="Source Type", size_hint_y=None, height=30, color=(0,0,0,1)))
        source_type_spinner = Spinner(
            text=node.get_property("source_type", "wave"),
            values=("wave", "file"),
            size_hint_y=None, height=40
        )
        
        def on_source_type_change(spinner, text):
            node.set_property("source_type", text)
            # Rebuild inspector to show relevant controls
            self.update_inspector(node)
            
        source_type_spinner.bind(text=on_source_type_change)
        self.content_area.add_widget(source_type_spinner)

        source_type = node.get_property("source_type", "wave")
        
        if source_type == "wave":
            self._build_wave_controls(node)
        else:
            self._build_file_controls(node)

    def _build_wave_controls(self, node):
        # Frequency Slider with Numeric Input
        self.content_area.add_widget(Label(text="Freq (Hz)", size_hint_y=None, height=30, color=(0,0,0,1)))
        
        freq_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=5)
        
        freq = node.get_property("frequency", 440)
        
        slider = Slider(min=1, max=2000, value=freq, size_hint_x=0.7)
        
        # Use Button for Numpad Trigger instead of TextInput
        freq_btn = Button(
            text=str(int(freq)), 
            size_hint_x=0.3,
            background_color=(0.9, 0.9, 0.9, 1),
            color=(0, 0, 0, 1)
        )
        
        def on_slider_change(instance, val):
            node.set_property("frequency", val)
            freq_btn.text = str(int(val))
            
        def on_freq_input(val):
            if val:
                try:
                    f = float(val)
                    if 1 <= f <= 20000:
                        node.set_property("frequency", f)
                        slider.value = f
                        freq_btn.text = str(int(f))
                except ValueError:
                    pass

        def open_numpad(instance):
            popup = NumericKeypadPopup(callback=on_freq_input, initial_value=freq_btn.text)
            popup.open()

        slider.bind(value=on_slider_change)
        freq_btn.bind(on_release=open_numpad)
        
        freq_layout.add_widget(slider)
        freq_layout.add_widget(freq_btn)
        self.content_area.add_widget(freq_layout)
        
        # Wave Type
        self.content_area.add_widget(Label(text="Wave", size_hint_y=None, height=30, color=(0,0,0,1)))
        spinner = Spinner(
            text=node.get_property("wave_type", "sine"),
            values=("sine", "square", "sawtooth"),
            size_hint_y=None, height=40
        )
        def on_wave_change(spinner, text):
            node.set_property("wave_type", text)
        spinner.bind(text=on_wave_change)
        self.content_area.add_widget(spinner)

    def _build_file_controls(self, node):
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup
        
        # File Selection Button
        file_path = node.get_property("file_path", "No file selected")
        
        select_btn = Button(
            text="Open file", 
            size_hint_y=None, 
            height=40,
            background_color=(0.2, 0.6, 1, 1), # Blue color to stand out
            color=(1, 1, 1, 1) # White text
        )
        
        # Label for selected file
        file_label_text = os.path.basename(file_path) if file_path != "No file selected" else "No file selected"
        file_label = Label(text=file_label_text, size_hint_y=None, height=30, color=(0,0,0,1))
        
        def show_file_chooser(instance):
            content = BoxLayout(orientation='vertical')
            # Use FileChooserListView for touch friendliness
            file_chooser = FileChooserListView(path=os.path.expanduser("~"), filters=['*.wav', '*.mp3', '*.ogg'])
            content.add_widget(file_chooser)
            
            btn_layout = BoxLayout(size_hint_y=None, height=50)
            select_btn_popup = Button(text="Select")
            cancel_btn_popup = Button(text="Cancel")
            btn_layout.add_widget(select_btn_popup)
            btn_layout.add_widget(cancel_btn_popup)
            content.add_widget(btn_layout)
            
            popup = Popup(title="Select Audio File", content=content, size_hint=(0.9, 0.9))
            
            def select_file(instance):
                if file_chooser.selection:
                    selected_file = file_chooser.selection[0]
                    node.set_property("file_path", selected_file)
                    # Update Label instead of Button
                    file_label.text = os.path.basename(selected_file)
                    
                    # Update file info
                    try:
                        channels, sr, duration = get_audio_info(selected_file)
                        node.set_property("channels", channels)
                        node.set_property("sample_rate", sr)
                        node.set_property("file_duration", duration)
                        # Set default end time to duration if 0
                        if node.get_property("end_time", 0.0) == 0.0:
                            node.set_property("end_time", duration)
                        
                        # Refresh inspector to show new info
                        self.update_inspector(node)
                    except Exception as e:
                        print(f"Error getting info: {e}")
                        
                    popup.dismiss()
                    
            select_btn_popup.bind(on_release=select_file)
            cancel_btn_popup.bind(on_release=popup.dismiss)
            
            popup.open()
            
        select_btn.bind(on_release=show_file_chooser)
        self.content_area.add_widget(Label(text="File", size_hint_y=None, height=30, color=(0,0,0,1)))
        self.content_area.add_widget(select_btn)
        self.content_area.add_widget(file_label)
        
        # File Info Display
        channels = node.get_property("channels", 0)
        duration = node.get_property("file_duration", 0.0)
        
        # Display in two lines to fit width
        self.content_area.add_widget(Label(text=f"Channels: {channels}", size_hint_y=None, height=30, color=(0,0,0,1)))
        self.content_area.add_widget(Label(text=f"Duration: {format_time(duration)}", size_hint_y=None, height=30, color=(0,0,0,1)))

        # File Playback Controls (Advanced)
        
        # Playback Mode (Loop/One Shot)
        self.content_area.add_widget(Label(text="Playback Mode", size_hint_y=None, height=30, color=(0,0,0,1)))
        loop_spinner = Spinner(
            text=node.get_property("playback_mode", "One Shot"),
            values=("One Shot", "Loop", "N Times"),
            size_hint_y=None, height=40
        )
        def on_loop_change(spinner, text):
            node.set_property("playback_mode", text)
        loop_spinner.bind(text=on_loop_change)
        self.content_area.add_widget(loop_spinner)

        # Start/End Trim (Seconds) with Numeric Input
        self.content_area.add_widget(Label(text="Trim Start/End", size_hint_y=None, height=30, color=(0,0,0,1)))
        
        # Trim Start Row
        start_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=5)
        start_row.add_widget(Label(text="Start:", size_hint_x=None, width=50, color=(0,0,0,1)))
        
        start_val = node.get_property("start_time", 0.0) # Changed from trim_start to start_time to match NodeTypes
        start_btn = Button(
            text=format_time(start_val), 
            size_hint_x=None, width=100, # Wider for time format
            background_color=(0.9, 0.9, 0.9, 1),
            color=(0, 0, 0, 1)
        )
        
        # Trim End Row
        end_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=5)
        end_row.add_widget(Label(text="End:", size_hint_x=None, width=50, color=(0,0,0,1)))
        
        end_val = node.get_property("end_time", 0.0) # Changed from trim_end to end_time
        end_btn = Button(
            text=format_time(end_val), 
            size_hint_x=None, width=100, # Wider for time format
            background_color=(0.9, 0.9, 0.9, 1),
            color=(0, 0, 0, 1)
        )
        
        def on_start_input(val):
            try:
                v = float(val)
                node.set_property("start_time", v)
                start_btn.text = format_time(v)
            except ValueError:
                pass
                
        def on_end_input(val):
            try:
                v = float(val)
                node.set_property("end_time", v)
                end_btn.text = format_time(v)
            except ValueError:
                pass

        def open_start_numpad(instance):
            # Pass current value in seconds for editing
            current = node.get_property("start_time", 0.0)
            NumericKeypadPopup(callback=on_start_input, initial_value=str(current)).open()
            
        def open_end_numpad(instance):
            current = node.get_property("end_time", 0.0)
            NumericKeypadPopup(callback=on_end_input, initial_value=str(current)).open()

        start_btn.bind(on_release=open_start_numpad)
        end_btn.bind(on_release=open_end_numpad)
        
        start_row.add_widget(start_btn)
        end_row.add_widget(end_btn)
        
        self.content_area.add_widget(start_row)
        self.content_area.add_widget(end_row)
        
        # Seek / Progress (Placeholder)
        self.content_area.add_widget(Label(text="Audio Position", size_hint_y=None, height=30, color=(0,0,0,1)))
        seek_slider = Slider(min=0, max=100, value=0, size_hint_y=None, height=40)
        # In a real app, this would bind to audio engine position
        self.content_area.add_widget(seek_slider)

    def _build_channel_inspector(self, node, graph=None):
        self.content_area.add_widget(Label(text="Output Mapping", size_hint_y=None, height=30, color=(0,0,0,1)))
        self.content_area.add_widget(Label(text=node.label, size_hint_y=None, height=30, color=(0,0,0,1)))
        
        # 1. Hardware Output Channel
        self.content_area.add_widget(Label(text="HW Channel", size_hint_y=None, height=30, color=(0,0,0,1)))
        
        # Determine used channels
        used_channels = []
        if graph:
            for n in graph.nodes.values():
                if n.id != node.id and n.type == NodeType.CHANNEL:
                    mapped = n.get_property("channel_index", 0)
                    if mapped > 0:
                        used_channels.append(mapped)
        
        current_val = node.get_property("channel_index", 0)
        values = ["None"]
        # Assume 8 channels max for now
        for i in range(1, 9):
            # Only show if not used by others, OR if it's the one currently used by this node
            if i not in used_channels or i == current_val:
                values.append(f"Channel {i}")
            
        current_text = "None"
        if current_val > 0:
            current_text = f"Channel {current_val}"
        
        spinner = Spinner(
            text=current_text,
            values=values,
            size_hint_y=None, height=40
        )
        
        def on_channel_change(spinner, text):
            if text.startswith("None"):
                node.set_property("channel_index", 0)
            else:
                try:
                    parts = text.split()
                    idx = int(parts[1])
                    node.set_property("channel_index", idx)
                except:
                    pass
            
        spinner.bind(text=on_channel_change)
        self.content_area.add_widget(spinner)

        # 2. Source Channel Selection
        self.content_area.add_widget(Label(text="Source Channel", size_hint_y=None, height=30, color=(0,0,0,1)))
        
        # Find connected source to determine available channels
        source_channels = 2 # Default
        if graph:
            input_conns = [c for c in graph.connections.values() if c.to_node_id == node.id]
            if input_conns:
                src = graph.nodes.get(input_conns[0].from_node_id)
                if src and src.type == NodeType.SOURCE:
                    source_channels = src.get_property("channels", 2)
                    if src.get_property("source_type") == "wave":
                        source_channels = 1
        
        src_values = ["Mix/Mono"]
        for i in range(1, source_channels + 1):
            src_values.append(f"Ch {i}")
            
        current_src_val = node.get_property("source_channel_index", 0)
        current_src_text = "Mix/Mono"
        if current_src_val > 0 and current_src_val <= source_channels:
            current_src_text = f"Ch {current_src_val}"
            
        src_spinner = Spinner(
            text=current_src_text,
            values=src_values,
            size_hint_y=None, height=40
        )
        
        def on_src_channel_change(spinner, text):
            if text.startswith("Mix"):
                node.set_property("source_channel_index", 0)
            else:
                try:
                    parts = text.split()
                    idx = int(parts[1])
                    node.set_property("source_channel_index", idx)
                except:
                    pass
        
        src_spinner.bind(text=on_src_channel_change)
        self.content_area.add_widget(src_spinner)


    def _build_trigger_inspector(self, node):
        self.content_area.add_widget(Label(text="Trigger Mode", size_hint_y=None, height=30, color=(0,0,0,1)))
        
        # Trigger Type Spinner
        trigger_spinner = Spinner(
            text=node.get_property("trigger_type", "on_start"),
            values=("on_start", "manual", "open"),
            size_hint_y=None, height=40
        )
        
        def on_trigger_type_change(spinner, text):
            node.set_property("trigger_type", text)
            
        trigger_spinner.bind(text=on_trigger_type_change)
        self.content_area.add_widget(trigger_spinner)
        
        # Manual Trigger Button (if needed for testing)
        btn = Button(text="TEST TRIGGER", size_hint_y=None, height=50)
        self.content_area.add_widget(btn)

class MainLayout(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Canvas (Bottom layer)
        self.node_canvas = NodeCanvas()
        self.add_widget(self.node_canvas)
        
        # Bottom Bar
        self.bottom_bar = BottomBar()
        self.bottom_bar.pos_hint = {'x': 0, 'y': 0}
        self.add_widget(self.bottom_bar)
        
        # Left Panel - REMOVED POS_HINT X CONSTRAINT
        self.left_panel = SidePanel(side='left')
        self.left_panel.pos_hint = {'top': 1} # Only vertical constraint
        self.add_widget(self.left_panel)
        
        # Right Panel - REMOVED POS_HINT X CONSTRAINT
        self.right_panel = SidePanel(side='right')
        self.right_panel.pos_hint = {'top': 1} # Only vertical constraint
        self.add_widget(self.right_panel)
        
        # Clock.schedule_once(self._init_panels, 0) # No longer needed if we rely on on_size, but good to have

    # def _init_panels(self, dt):
    #     self.left_panel._update_position()
    #     self.right_panel._update_position()
