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

import requests
import json
import logging
import time
from typing import Dict, Any, Tuple
import urllib3
from icinga2_passive_replicator.connection import ConnectionException, NotExistsException, SinkException
from icinga2_passive_replicator.containers import Host, Service, Hosts, Services

DEFAULT_VAR_PASSIVE_REPLICATOR = "i2pr"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class Sink:

    def __init__(self):
        self.user = ''
        self.passwd = ''
        self.host = ''
        self.headers = {'Accept': 'application/json'}
        self.verify = False
        self.retries = 5
        self.timeout = 5
        self.vars_prefix = 'i2pr_'
        self.host_template = 'generic-host'
        self.service_template = 'generic-service'
        self.check_command = 'dummy'
        self.hostgroups = ['i2pr']
        self._url_passive_check = self.host + '/v1/actions/process-check-result'
        self._url_host_create = self.host + '/v1/objects/hosts'
        self._url_service_create = self.host + '/v1/objects/services'
        self._url_hostgroup_create = self.host + '/v1/objects/hostgroups'

    def validate_preconditions(self) -> None:
        for hostgroup in self.hostgroups:

            create_body = {
                "attrs": {"display_name": hostgroup}
            }
            data, status = self._get(f"{self._url_hostgroup_create}/{hostgroup}")
            if status != 200:
                self._put(f"{self._url_hostgroup_create}/{hostgroup}", create_body)
                logger.info(f"message=\"Created missing hostgroup\" hostgroup={hostgroup}")

    def push(self, hs: Any) -> int:
        """
        Push data to the sink instance
        :param hs:
        :return: The number of passive checks executed
        """
        count = 0
        try:
            if isinstance(hs, Hosts):
                for name, host in hs.get().items():
                    count += 1
                    self.host_passive_check(host)
            elif isinstance(hs, Services):
                for name, service in hs.get().items():
                    count += 1
                    self.service_passive_check(service)
            else:
                logger.warning(f"message=\"Not a valid object\"")
        except Exception as err:
            logger.warning(f"message=\"Push to sink failed unexpectedly\" error=\"{err}\"")
            raise SinkException(err)

        return count

    def host_passive_check(self, host: Host) -> None:
        """
        Execute passive check for host. If host does not exist it will be created
        throws ConnectionException if any connection errors
        :param host:
        :return:

        """
        body = {
            "type": "Host",
            "plugin_output": host.output,
            "performance_data": host.performance_data,
            "exit_status": host.exit_status
        }

        try:
            self._post(f"{self._url_passive_check}?host={host.name}", body)
        except NotExistsException:
            # Create missing host
            create_body = {
                "templates": [self.host_template],
                "attrs": {"check_command": self.check_command,
                          "groups": self.hostgroups,
                          "enable_active_checks": False,
                          "enable_passive_checks": True,
                          "vars": {DEFAULT_VAR_PASSIVE_REPLICATOR: True}
                          }
            }

            if host.vars:
                for key, value in host.vars.items():
                    create_body['attrs']['vars'][f"{self.vars_prefix}{key}"] = value

            self._put(f"{self._url_host_create}/{host.name}", create_body)
            logger.info(f"message=\"Created missing host\" host_name={host.name}")

    def service_passive_check(self, service: Service) -> None:
        """
        Execute passive check for service. If service does not exist it will be created
        :param service:
        :return:
        """
        body = {
            "type": "Service",
            "plugin_output": service.output,
            "performance_data": service.performance_data,
            "exit_status": service.exit_status
        }

        try:
            self._post(f"{self._url_passive_check}?service={service.name}", body)
        except NotExistsException:
            # Create missing service
            create_body = {
                "templates": [self.service_template],
                "attrs": {"display_name": service.display_name,
                          "check_command": self.check_command,
                          "enable_active_checks": False,
                          "enable_passive_checks": True,
                          "vars": {DEFAULT_VAR_PASSIVE_REPLICATOR: True},
                          }
            }

            if service.vars:
                for key, value in service.vars.items():
                    create_body['attrs']['vars'][f"{self.vars_prefix}{key}"] = value

            self._put(f"{self._url_service_create}/{service.name}", create_body)
            logger.info(f"message=\"Created missing service\" service_name=\"{service.name}\"")

    def _post(self, url, body=None) -> Dict[str, Any]:
        """
        Do a POST call
        :param url:
        :param body:
        :return:
        """
        try:
            with requests.Session() as session:
                start_time = time.monotonic()
                session.auth = (self.user, self.passwd)
                with session.post(f"{self.host}{url}",
                                  verify=self.verify,
                                  timeout=self.timeout,
                                  headers=self.headers,
                                  data=json.dumps(body)) as response:
                    logger.info(f"message=\"Call sink\" host={self.host} method=post "
                                f"url=\"{url}\" status={response.status_code} "
                                f"response_time={time.monotonic() - start_time}")

                    if response.status_code == 404:
                        logger.warning(f"message=\"{response.reason}\" status={response.status_code}")
                        raise NotExistsException(message=f"Http status {response.status_code}")

                    if response.status_code != 200 and response.status_code != 201:
                        logger.warning(f"message=\"{response.reason}\" status={response.status_code}")
                        logger.debug(f"message=\"Failed body\" body=\"{body}")
                        raise ConnectionException(message=f"Http status {response.status_code}", err=None,
                                                  url=self.host)

                    return json.loads(response.text)

        except requests.exceptions.RequestException as err:
            logger.error(f"message=\"Error from connection\" error=\"{err}\"")
            raise ConnectionException(message=f"Error from connection", err=err, url=self.host)

    def _put(self, url, body=None) -> Dict[str, Any]:
        """
        Do a PUT call
        :param url:
        :param body:
        :return:
        """
        try:
            with requests.Session() as session:
                start_time = time.monotonic()
                session.auth = (self.user, self.passwd)
                with session.put(f"{self.host}{url}",
                                 verify=self.verify,
                                 timeout=self.timeout,
                                 headers=self.headers,
                                 data=json.dumps(body)) as response:
                    logger.info(f"message=\"Call sink\" host={self.host} method=put "
                                f"url=\"{url}\" status= {response.status_code} "
                                f"response_time={time.monotonic() - start_time}")

                    if response.status_code == 404:
                        logger.warning(f"message=\"{response.reason}\" status={response.status_code}")
                        raise NotExistsException(message=f"Http status {response.status_code}")

                    if response.status_code != 200 and response.status_code != 201:
                        logger.warning(f"message=\"{response.reason}\" status={response.status_code}")
                        raise ConnectionException(message=f"Http status {response.status_code}", err=None,
                                                  url=self.host)

                    return json.loads(response.text)

        except requests.exceptions.RequestException as err:
            logger.error(f"message=\"Error from connection\" error={err}")
            raise ConnectionException(message=f"Error from connection", err=err, url=self.host)

    def _get(self, url) -> Tuple[Dict[str, Any], int]:
        """
        Do a PUT call
        :param url:
        :return:
        """
        try:
            with requests.Session() as session:
                start_time = time.monotonic()
                session.auth = (self.user, self.passwd)
                with session.get(f"{self.host}{url}",
                                 verify=self.verify,
                                 timeout=self.timeout,
                                 headers=self.headers) as response:
                    logger.info(f"message=\"Call sink\" host={self.host} method=get "
                                f"url=\"{url}\" status= {response.status_code} "
                                f"response_time={time.monotonic() - start_time}")

                    return json.loads(response.text), response.status_code

        except requests.exceptions.RequestException as err:
            logger.error(f"message=\"Error from connection\" error={err}")
            raise ConnectionException(message=f"Error from connection", err=err, url=self.host)
