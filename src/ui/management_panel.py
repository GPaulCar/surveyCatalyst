from management.service import ManagementService

class ManagementPanel:
    def __init__(self):
        self.service = ManagementService()

    def show_status(self):
        status = self.service.get_db_status()
        print("DB Status:", status)
