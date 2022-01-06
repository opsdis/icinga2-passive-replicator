# -*- coding: utf-8 -*-
"""
    Copyright (C) 2022 Redbridge AB

    This file is part of icinga2-passive-replicator (i2pr).

    i2pr is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    i2pr is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with i2pr.  If not, see <http://www.gnu.org/licenses/>.

"""

from typing import Dict, Any, List


class IcingaObject:
    def __init__(self):
        self.name: str = ''
        self.display_name = ''
        self.vars: Dict[str, Any] = {}
        self.performance_data: List[str] = []
        self.output: str = ''
        self.exit_status: int = 0


class Service(IcingaObject):
    def __init__(self):
        super().__init__()
        self.host_name = ''


class Host(IcingaObject):
    def __init__(self):
        super().__init__()


class Hosts:
    def __init__(self):
        self._hosts: Dict[str, Host] = {}

    def add(self, obj: Host):
        self._hosts[obj.name] = obj

    def get(self) -> Dict[str, Host]:
        return self._hosts


class Services:
    def __init__(self):
        self._services: Dict[str, Service] = {}

    def add(self, obj: Service):
        self._services[obj.name] = obj

    def get(self) -> Dict[str, Service]:
        return self._services
