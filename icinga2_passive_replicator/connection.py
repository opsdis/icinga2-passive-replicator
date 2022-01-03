class ConnectionExecption(Exception):
    def __init__(self, message: str, err: Exception = None, url: str = None):
        self.message = message
        self.err = err
        self.url = url


class NotExistsExecption(Exception):
    def __init__(self, message: str):
        self.message = message


class SourceExecption(Exception):
    def __init__(self, message: str):
        self.message = message


class SinkExecption(Exception):
    def __init__(self, message: str):
        self.message = message
