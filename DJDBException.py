class DJDBException(Exception):
    def __init__(self, message="DJ DB error"):
        self.message = message
        super().__init__(self.message)
    def __str__(self):
        return self.message