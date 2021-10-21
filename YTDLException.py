class YTDLException(Exception):
    def __init__(self, message="Youtube download error"):
        self.message = message
        super().__init__(self.message)