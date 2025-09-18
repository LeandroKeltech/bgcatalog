from kivy.app import App
from kivy.uix.label import Label

class MainApp(App):
    def build(self):
        return Label(text='BGCatalog App - Hello World!')

if __name__ == '__main__':
    MainApp().run()
