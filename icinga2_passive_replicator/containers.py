from typing import Dict, Any, List


class IcingaObject:
    def __init__(self):
        self.name: str = ''
        self.vars: Dict[str, Any] = {}
        self.performance_data: List[str] = []
        self.output: str = ''
        self.exit_status: int = 0


class Service(IcingaObject):
    def __init__(self):
        super().__init__()
        self.host_name = ''
        self.display_name = ''


class Host(IcingaObject):
    def __init__(self):
        super().__init__()


class Hosts:
    def __init__(self):
        self._hosts: Dict[str, Host] = {}

    def add(self, obj: Host):
        self._hosts[obj.name] = obj

    def get(self) -> Dict[str, Host]:
        return self._hosts.items()


class Services:
    def __init__(self):
        self._services: Dict[str, Service] = {}

    def add(self, obj: Service):
        self._services[obj.name] = obj

    def get(self) -> Dict[str, Service]:
        return self._services.items()
