class MapController:
    def __init__(self):
        self.current = None

    def focus_geometry(self, geom):
        self.current = geom
        print("Focus:", geom)
