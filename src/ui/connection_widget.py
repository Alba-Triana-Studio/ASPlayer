from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Bezier
from kivy.graphics.instructions import InstructionGroup
from kivy.uix.button import Button
from kivy.core.window import Window
import math

class ConnectionWidget(Widget):
    def __init__(self, connection_id, source_widget, target_widget, controller, **kwargs):
        super().__init__(**kwargs)
        self.connection_id = connection_id
        self.source_widget = source_widget
        self.target_widget = target_widget
        self.controller = controller
        self.selected = False
        self.delete_btn = None
        
        # Create instruction group for the line to avoid clearing children (buttons)
        self.line_group = InstructionGroup()
        self.canvas.add(self.line_group)
        
        # Bind to position changes of source/target widgets
        self.source_widget.bind(pos=self.update_line, size=self.update_line)
        self.target_widget.bind(pos=self.update_line, size=self.update_line)
        
        # Draw initially
        self.update_line()

    def update_line(self, *args):
        self.line_group.clear()
        
        # Calculate points
        if not self.source_widget or not self.target_widget:
            return
            
        # From Output Pin (Right side of from_widget)
        x1 = self.source_widget.right
        y1 = self.source_widget.center_y
        
        # To Input Pin (Left side of to_widget)
        x2 = self.target_widget.x
        y2 = self.target_widget.center_y
        
        # Control Points
        cx1 = x1 + 50
        cy1 = y1
        cx2 = x2 - 50
        cy2 = y2
        
        self.points = [x1, y1, cx1, cy1, cx2, cy2, x2, y2]
        
        if self.selected:
            self.line_group.add(Color(1, 0, 0, 1)) # Red if selected
            width = 2.5
        else:
            self.line_group.add(Color(0.2, 0.2, 0.2, 1))
            width = 1.5
            
        self.line_group.add(Line(bezier=self.points, width=width))
            
        # Update delete button position if selected
        if self.selected and self.delete_btn:
            # Place at midpoint of bezier (approximate)
            mx, my = self.calculate_bezier_point(0.5, self.points)
            self.delete_btn.center = (mx, my)

    def calculate_bezier_point(self, t, points):
        # Cubic Bezier: B(t) = (1-t)^3 P0 + 3(1-t)^2 t P1 + 3(1-t) t^2 P2 + t^3 P3
        p0x, p0y = points[0], points[1]
        p1x, p1y = points[2], points[3]
        p2x, p2y = points[4], points[5]
        p3x, p3y = points[6], points[7]
        
        u = 1 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t
        
        x = uuu * p0x + 3 * uu * t * p1x + 3 * u * tt * p2x + ttt * p3x
        y = uuu * p0y + 3 * uu * t * p1y + 3 * u * tt * p2y + ttt * p3y
        
        return x, y

    def on_touch_down(self, touch):
        # Let children handle it first (e.g. delete button)
        if super().on_touch_down(touch):
            return True

        # Check collision with the curve
        if self.collide_bezier(touch.pos):
            self.select()
            return True
        else:
            # Deselect if clicked outside
            if self.selected:
                self.deselect()
        
        return False

    def collide_bezier(self, pos):
        # Check distance to the curve
        # We sample 20 points along the curve
        threshold = 20 # pixels - increased for better touch accessibility
        px, py = pos
        
        for i in range(21):
            t = i / 20.0
            bx, by = self.calculate_bezier_point(t, self.points)
            dist = math.hypot(px - bx, py - by)
            if dist < threshold:
                return True
        return False

    def select(self):
        if self.selected: return
        self.selected = True
        
        # Add Delete Button
        self.delete_btn = Button(text="X", size_hint=(None, None), size=(30, 30), background_color=(1, 0, 0, 1))
        self.delete_btn.bind(on_release=self.delete_connection)
        self.add_widget(self.delete_btn)
        
        self.update_line()

    def deselect(self):
        if not self.selected: return
        self.selected = False
        
        if self.delete_btn:
            self.remove_widget(self.delete_btn)
            self.delete_btn = None
            
        self.update_line()

    def delete_connection(self, instance):
        if self.controller:
            self.controller.remove_connection(self.connection_id)
