from map.controller import MapController

class App:
    def __init__(self):
        self.map = MapController()

    def run(self):
        print("App started")
