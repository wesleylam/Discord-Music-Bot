class DJBannedException(Exception):
    def __init__(self, message="DJ banned"):
        self.message = message
        super().__init__(self.message)
    def __str__(self):
        return self.message