from kivy.lang import Builder
from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, Screen

class HomeScreen(Screen):
    pass

class ItemFormScreen(Screen):
    pass

class ReviewScreen(Screen):
    pass

class InventoryScreen(Screen):
    pass

class ExportScreen(Screen):
    pass

class SettingsScreen(Screen):
    pass

class MainApp(MDApp):
    def build(self):
        self.title = 'Catalog App'
        Builder.load_file('kv/main.kv')
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(ItemFormScreen(name='item_form'))
        sm.add_widget(ReviewScreen(name='review'))
        sm.add_widget(InventoryScreen(name='inventory'))
        sm.add_widget(ExportScreen(name='export'))
        sm.add_widget(SettingsScreen(name='settings'))
        return sm

    def open_settings(self):
        self.root.current = 'settings'

    def go_home(self):
        self.root.current = 'home'

    def open_new_item(self):
        self.root.current = 'item_form'

    def save_item(self):
        # Placeholder for save logic
        self.go_home()

    def export_to_sheets(self):
        # Placeholder for export logic
        pass

    def save_settings(self):
        # Placeholder for settings save logic
        self.go_home()

    def filter_items(self, text):
        # Placeholder for filter logic
        pass

    def on_tab_switch(self, instance_tabs, instance_tab, instance_tab_label, tab_text):
        # Placeholder for tab switch logic
        pass

if __name__ == '__main__':
    MainApp().run()
