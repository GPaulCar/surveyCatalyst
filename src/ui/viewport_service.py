class ViewportService:
    def __init__(self):
        self.bounds = None

    def set_bounds(self, bounds):
        self.bounds = bounds

    def get_bounds(self):
        return self.bounds
