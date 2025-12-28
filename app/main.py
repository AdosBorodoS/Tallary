import os

os.environ["KIVY_WINDOW"] = "sdl2"
os.environ["KIVY_GL_BACKEND"] = "sdl2"

from kivy.config import Config
from kivymd.app import MDApp

from app.app import TallaryUiApp
# from kivy.core.window import Window
# Window.clearcolor = (0, 0, 0, 1)
isDesktopPreview = os.environ.get("TALLARY_PREVIEW", "1") == "1"

if isDesktopPreview:
    Config.set("graphics", "width", "360")
    Config.set("graphics", "height", "800")
    Config.set("graphics", "resizable", "0")
    Config.set("input", "mouse", "mouse,multitouch_on_demand")


class TallaryApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.material_style = "M2"
        return TallaryUiApp().build()


if __name__ == "__main__":
    TallaryApp().run()
