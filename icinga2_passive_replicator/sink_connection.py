import requests
import json
import logging
import time
from typing import Dict, Any
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
        self.url_passive_check = self.host + '/v1/actions/process-check-result'
        self.url_host_create = self.host + '/v1/objects/hosts'
        self.url_service_create = self.host + '/v1/objects/services'

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
            self._post(f"{self.url_passive_check}?host={host.name}", body)
        except NotExistsException:
            # Create missing host
            create_body = {
                "templates": [self.host_template],
                "attrs": {"check_command": self.check_command,
                          "enable_active_checks": False,
                          "enable_passive_checks": True,
                          "vars": {DEFAULT_VAR_PASSIVE_REPLICATOR: True}
                          }
            }

            if host.vars:
                for key, value in host.vars.items():
                    create_body['attrs']['vars'][f"{self.vars_prefix}{key}"] = value

            self._put(f"{self.url_host_create}/{host.name}", create_body)
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
            self._post(f"{self.url_passive_check}?service={service.name}", body)
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

            self._put(f"{self.url_service_create}/{service.name}", create_body)
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
