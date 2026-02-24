from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.properties import ObjectProperty, BooleanProperty, ListProperty, NumericProperty
from src.core.node import NodeType

class PinWidget(Widget):
    def __init__(self, is_input=True, parent_node_widget=None, **kwargs):
        super().__init__(**kwargs)
        self.is_input = is_input
        self.parent_node_widget = parent_node_widget
        self.size = (20, 20) # Increased for better touch
        
        with self.canvas:
            Color(0, 0, 0, 1)
            self.shape = Ellipse(pos=self.pos, size=self.size)
            
        self.bind(pos=self._update_pos, size=self._update_pos)

    def _update_pos(self, *args):
        self.shape.pos = self.pos
        self.shape.size = self.size

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.parent_node_widget:
                # self.parent_node_widget.on_pin_touch(self, touch) # Old way
                
                # Start Dragging Connection
                if self.parent_node_widget.controller:
                    self.parent_node_widget.controller.start_connection_drag(
                        self.parent_node_widget.node, 
                        self.is_input
                    )
                touch.grab(self)
                return True
        return False

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            if self.parent_node_widget.controller:
                self.parent_node_widget.controller.update_connection_drag(touch.pos)
            return True
        return False

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            
            # Check if dropped on another pin
            # This is tricky because touch_up is on the source pin, we need to find if we are over a target pin
            # We can ask the controller or iterate widgets. 
            # A simpler way is to check collision with all pin widgets in the system, 
            # but we don't have global access easily here.
            
            # Better approach: The controller knows all widgets. Let the controller handle "drop" check?
            # Or we can do a hit test on the canvas children.
            
            target_node = None
            target_is_input = False
            
            # Find target pin
            # We need to access the root canvas to find other widgets
            canvas = self.parent_node_widget.parent
            if canvas:
                # Convert touch pos to local coords if needed (usually global)
                for widget in canvas.children:
                    if isinstance(widget, NodeWidget) and widget != self.parent_node_widget:
                        if widget.input_pin and widget.input_pin.collide_point(*touch.pos):
                            target_node = widget.node
                            target_is_input = True
                            break
                        if widget.output_pin and widget.output_pin.collide_point(*touch.pos):
                            target_node = widget.node
                            target_is_input = False
                            break
            
            if self.parent_node_widget.controller:
                self.parent_node_widget.controller.end_connection_drag(target_node, target_is_input)
                
                # Fallback: If no target, but it was a click (no move), trigger old behavior (auto-create)
                # Distance check?
                # If drag distance was small... but we don't track start pos here easily.
                # Actually, if target_node is None, we can treat it as a click if desired.
                # User requirement 2: "Al hacer click en el pin out ... debe poder hacerse un nuevo cable"
                # This implies drag and drop. 
                # User requirement 1: "Un nodo chanel no puede generar diferentes nodos sourse" -> Handled in controller
                
                # If it was a simple click on Input Pin (backward flow), we might still want that feature?
                # User said: "Al hacer click en el pin out ... debe poder hacerse un nuevo cable"
                # This sounds like Drag from Output.
                # What about Input? "Un nodo chanel no puede generar diferentes nodos sourse"
                # This implies the old auto-create behavior is still valid but restricted.
                
                if not target_node and self.is_input:
                     # Only trigger auto-create if it was a click on Input Pin
                     # We can assume it's a click if no drag happened? 
                     # Let's just call handle_pin_click if no target found.
                     self.parent_node_widget.controller.handle_pin_click(self.parent_node_widget.node, self.is_input)
            
            return True
        return False

class NodeWidget(Widget):
    node = ObjectProperty(None)
    selected = BooleanProperty(False)
    color = ListProperty([0, 0, 0, 1])
    
    def __init__(self, node, controller=None, **kwargs):
        super().__init__(**kwargs)
        self.node = node
        self.controller = controller
        self.size_hint = (None, None) # Important: Disable auto-sizing in FloatLayout
        self.size = (80, 50) # Reduced size for 3.5" screen
        self.pos = node.position
        
        with self.canvas.before:
            # Background
            self.bg_color = Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            # Border
            self.border_color = Color(0, 0, 0, 1)
            self.border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=1.2)

        self.label_widget = Label(text=node.label, color=(0,0,0,1), center=self.center, font_size='8sp')
        self.add_widget(self.label_widget)
        
        # Pins
        self.input_pin = None
        self.output_pin = None
        
        if self.node.type != NodeType.TRIGGER:
            self.input_pin = PinWidget(is_input=True, parent_node_widget=self)
            self.add_widget(self.input_pin)
            
        if self.node.type != NodeType.CHANNEL:
            self.output_pin = PinWidget(is_input=False, parent_node_widget=self)
            self.add_widget(self.output_pin)
        
        self.bind(pos=self._update_graphics, size=self._update_graphics)
        self.bind(selected=self._on_selected)
        self._update_graphics(self, None)

    def _update_graphics(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)
        self.label_widget.center = instance.center
        
        # Position Pins
        if self.input_pin:
            self.input_pin.center_x = self.x
            self.input_pin.center_y = self.center_y
            
        if self.output_pin:
            self.output_pin.center_x = self.right
            self.output_pin.center_y = self.center_y
        
        # Update underlying node position
        if self.node:
            self.node.position = instance.pos

    def _on_selected(self, instance, value):
        if value:
            self.border_line.width = 2.5
        else:
            self.border_line.width = 1.2

    def on_touch_down(self, touch):
        # Check pins first
        if self.input_pin and self.input_pin.on_touch_down(touch):
            return True
        if self.output_pin and self.output_pin.on_touch_down(touch):
            return True
            
        if self.collide_point(*touch.pos):
            # Propagate selection first (so panel opens)
            if self.controller:
                self.controller.select_node(self.node)
                
            self.selected = True
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self.pos = (self.x + touch.dx, self.y + touch.dy)
            # Notify controller to redraw connections
            if self.controller:
                self.controller.update_connections_view()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)

    def on_pin_touch(self, pin, touch):
        if pin.is_input:
            print(f"Input pin touched on {self.node.label}")
            if self.controller:
                self.controller.handle_pin_click(self.node, is_input=True)
