class DJBannedException(Exception):
    def __init__(self, message="DJ banned"):
        self.message = message
        super().__init__(self.message)
    def __str__(self):
        return self.message

class DJDBException(Exception):
    def __init__(self, message="DJ DB error"):
        self.message = message
        super().__init__(self.message)
    def __str__(self):
        return self.message

class DJSongNotFoundException(Exception):
    def __init__(self, message="Song not found"):
        self.message = message
        super().__init__(self.message)
    def __str__(self):
        return self.message