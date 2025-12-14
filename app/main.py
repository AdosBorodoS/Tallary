from kivy.app import App
from app.app import TallaryUiApp


class TallaryApp(App):
    def build(self):
        return TallaryUiApp().build()


if __name__ == "__main__":
    TallaryApp().run()
