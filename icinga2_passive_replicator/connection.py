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
