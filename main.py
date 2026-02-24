import kivy
kivy.require('2.3.0')

# Configure Kivy before importing App/Window
from kivy.config import Config
# Limit FPS to save CPU for audio processing
Config.set('graphics', 'maxfps', '30')
# Allow input without mouse cursor (for touchscreens)
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.app import App
from kivy.core.window import Window
from src.ui.layout import MainLayout
from src.ui.controller import Controller

# Configuración inicial de ventana (Fullscreen, sin bordes)
# Nota: En desarrollo se puede comentar 'fullscreen' para facilitar el debug
Window.fullscreen = 'auto'
Window.borderless = True
# Window.size = (480, 320) # Comentado para que tome la resolución nativa en fullscreen

class ASPlayerApp(App):
    def build(self):
        self.controller = Controller()
        layout = MainLayout()
        self.controller.set_ui(layout)
        return layout




if __name__ == '__main__':
    ASPlayerApp().run()
