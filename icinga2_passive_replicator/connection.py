class ConnectionException(Exception):
    def __init__(self, message: str, err: Exception = None, url: str = None):
        self.message = message
        self.err = err
        self.url = url


class NotExistsException(Exception):
    def __init__(self, message: str):
        self.message = message


class SourceException(Exception):
    def __init__(self, exception: Exception):
        self.exception = exception


class SinkException(Exception):
    def __init__(self, exception: Exception):
        self.exception = exception
