from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Color, Rectangle
import os

class AlphaNumericKeypadPopup(BoxLayout):
    def __init__(self, callback, initial_value="", **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.callback = callback
        self.current_value = str(initial_value)
        
        # Display
        self.display = Label(text=self.current_value, size_hint_y=None, height=40, font_size='20sp', color=(1,1,1,1))
        with self.canvas.before:
            Color(0.2, 0.2, 0.2, 1)
            Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_rect)
        
        self.add_widget(self.display)
        
        # Keyboard Layout
        # Simple QWERTY
        rows = [
            ['1','2','3','4','5','6','7','8','9','0'],
            ['q','w','e','r','t','y','u','i','o','p'],
            ['a','s','d','f','g','h','j','k','l'],
            ['z','x','c','v','b','n','m', '_', '-', '.']
        ]
        
        kb_layout = BoxLayout(orientation='vertical', spacing=2)
        
        for row_keys in rows:
            row_layout = BoxLayout(orientation='horizontal', spacing=2)
            for key in row_keys:
                btn = Button(text=key, font_size='18sp')
                btn.bind(on_release=self.on_key_press)
                row_layout.add_widget(btn)
            kb_layout.add_widget(row_layout)
            
        self.add_widget(kb_layout)
        
        # Special Keys Row
        special_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=45, spacing=2)
        
        bs_btn = Button(text="Bksp", background_color=(0.8, 0.4, 0.4, 1))
        bs_btn.bind(on_release=self.on_backspace)
        special_row.add_widget(bs_btn)
        
        space_btn = Button(text="Space")
        space_btn.bind(on_release=lambda x: self.on_key_press(type('obj', (object,), {'text': ' '})(text=' ')))
        special_row.add_widget(space_btn)
        
        clear_btn = Button(text="Clear", background_color=(0.8, 0.4, 0.4, 1))
        clear_btn.bind(on_release=self.on_clear)
        special_row.add_widget(clear_btn)
        
        self.add_widget(special_row)

        # Actions
        actions = BoxLayout(size_hint_y=None, height=45, spacing=5, padding=(0,5,0,0))
        cancel_btn = Button(text="Cancel", background_color=(0.8, 0.2, 0.2, 1))
        cancel_btn.bind(on_release=self.cancel)
        ok_btn = Button(text="OK", background_color=(0.2, 0.8, 0.2, 1))
        ok_btn.bind(on_release=self.confirm)
        
        actions.add_widget(cancel_btn)
        actions.add_widget(ok_btn)
        self.add_widget(actions)
        
        # Popup wrapper
        self.popup = Popup(title="Enter Text", content=self, size_hint=(0.95, 0.95))

    def _update_bg(self, instance, value):
        pass 
        
    def _update_rect(self, instance, value):
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
        self.current_value += instance.text
        self.display.text = self.current_value
        
    def on_backspace(self, instance):
        self.current_value = self.current_value[:-1]
        self.display.text = self.current_value
        
    def on_clear(self, instance):
        self.current_value = ""
        self.display.text = self.current_value

class SaveDialog(BoxLayout):
    def __init__(self, save_callback, cancel_callback, default_filename="workspace.json", **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.save_callback = save_callback
        self.cancel_callback = cancel_callback
        self.filename = default_filename
        
        # File Chooser to browse directories
        self.file_chooser = FileChooserListView(path=os.getcwd(), filters=["*.json"])
        self.file_chooser.bind(selection=self.on_selection)
        self.add_widget(self.file_chooser)
        
        # Filename Input (Button triggering Keypad)
        input_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        input_layout.add_widget(Label(text="Filename:", size_hint_x=None, width=80))
        
        self.filename_btn = Button(text=self.filename, background_color=(0.9, 0.9, 0.9, 1), color=(0,0,0,1))
        self.filename_btn.bind(on_release=self.open_keyboard)
        input_layout.add_widget(self.filename_btn)
        
        self.add_widget(input_layout)
        
        # Buttons
        btn_layout = BoxLayout(size_hint_y=None, height=50)
        save_btn = Button(text="Save")
        save_btn.bind(on_release=self.save)
        cancel_btn = Button(text="Cancel")
        cancel_btn.bind(on_release=self.cancel)
        
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(cancel_btn)
        self.add_widget(btn_layout)
        
    def on_selection(self, instance, selection):
        if selection:
            self.filename = os.path.basename(selection[0])
            self.filename_btn.text = self.filename
            
    def open_keyboard(self, instance):
        AlphaNumericKeypadPopup(callback=self.on_filename_input, initial_value=self.filename).open()
        
    def on_filename_input(self, value):
        self.filename = value
        self.filename_btn.text = self.filename
        
    def save(self, instance):
        path = self.file_chooser.path
        if not self.filename:
            return
            
        # Auto-append .json extension
        if not self.filename.lower().endswith('.json'):
            self.filename += '.json'
            
        full_path = os.path.join(path, self.filename)
        
        # Check for overwrite
        if os.path.exists(full_path):
            self._show_overwrite_popup(full_path)
        else:
            if self.save_callback:
                self.save_callback(path, self.filename)

    def _show_overwrite_popup(self, full_path):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Increase size hint for the label to ensure it has space, or better, use size_hint_y=None with height
        # But letting it expand is usually best if the popup has enough height.
        # The main issue is likely the popup size_hint=(0.8, 0.4) is too small on small screens.
        
        msg = f"File '{self.filename}' already exists.\nOverwrite?"
        label = Label(text=msg, halign='center', valign='middle')
        label.bind(size=lambda s, w: s.setter('text_size')(s, w))
        content.add_widget(label)
        
        btn_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        yes_btn = Button(text="Yes", background_color=(0.8, 0.2, 0.2, 1))
        no_btn = Button(text="No")
        
        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        content.add_widget(btn_layout)
        
        # Increased size_hint to 0.5 to give more vertical room
        popup = Popup(title="Confirm Overwrite", content=content, size_hint=(0.8, 0.5))
        
        def on_yes(instance):
            popup.dismiss()
            if self.save_callback:
                self.save_callback(self.file_chooser.path, self.filename)
                
        def on_no(instance):
            popup.dismiss()
            
        yes_btn.bind(on_release=on_yes)
        no_btn.bind(on_release=on_no)
        popup.open()
            
    def cancel(self, instance):
        if self.cancel_callback:
            self.cancel_callback()

class LoadDialog(BoxLayout):
    def __init__(self, load_callback, cancel_callback, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.load_callback = load_callback
        self.cancel_callback = cancel_callback
        
        # File Chooser
        self.file_chooser = FileChooserListView(path=os.getcwd(), filters=["*.json"])
        self.add_widget(self.file_chooser)
        
        # Buttons
        btn_layout = BoxLayout(size_hint_y=None, height=50)
        load_btn = Button(text="Load")
        load_btn.bind(on_release=self.load)
        cancel_btn = Button(text="Cancel")
        cancel_btn.bind(on_release=self.cancel)
        
        btn_layout.add_widget(load_btn)
        btn_layout.add_widget(cancel_btn)
        self.add_widget(btn_layout)
        
    def load(self, instance):
        selection = self.file_chooser.selection
        if selection:
            if self.load_callback:
                self.load_callback(selection[0])
        
    def cancel(self, instance):
        if self.cancel_callback:
            self.cancel_callback()
