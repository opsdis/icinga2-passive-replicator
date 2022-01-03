import requests
import json
import logging
import time
from typing import Dict, Any
import urllib3
from icinga2_passive_replicator.connection import ConnectionExecption

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class Source:

    def __init__(self):
        """
        The constructor takes on single argument that is a config dict
        :param config:
        """
        self.user = ''
        self.passwd = ''
        self.host = ''
        self.headers = {'content-type': 'application/json'}
        self.verify = False
        self.retries = 5
        self.timeout = 5
        self.hostgroup = ''

        self.url_query_services = self.host + '/v1/objects/services'
        self.url_query_hosts = self.host + '/v1/objects/hosts'

    def get_host_data(self) -> Dict[str, Any]:
        """
        Get host data
        :return:
        """
        body = {
            "type": "Host",
            "attrs": ["name", "last_check_result", "vars"],
            "filter": '\"{}\" in host.groups'.format(self.hostgroup)
        }

        data_json = self._post(self.url_query_hosts, body)

        return data_json

    def get_service_data(self) -> Dict[str, Any]:
        """
        Get service data
        :return:
        """
        body = {
            "type": "Service",
            "joins": ["host.name"],
            "attrs": ["display_name", "last_check_result", "vars"],
            "filter": '\"{}\" in host.groups'.format(self.hostgroup)
        }

        data_json = self._post(self.url_query_services, body)

        return data_json

    def _post(self, url, body=None) -> Dict[str, Any]:

        try:
            with requests.Session() as session:
                start_time = time.monotonic()
                session.auth = (self.user, self.passwd)
                with session.post(f"{self.host}{url}",
                                  verify=self.verify,
                                  timeout=self.timeout,
                                  headers={'Content-Type': 'application/json',
                                           'X-HTTP-Method-Override': 'GET'},
                                  data=json.dumps(body)) as response:
                    logger.debug(f"request", {'method': 'post', 'url': url, 'status': response.status_code,
                                              'response_time': time.monotonic() - start_time})
                    if response.status_code != 200 and response.status_code != 201:
                        logger.warning(f"{response.reason} status {response.status_code}")
                        raise ConnectionExecption(message=f"Http status {response.status_code}", err=None,
                                                  url=self.host)

                    return json.loads(response.text)

        except requests.exceptions.RequestException as err:
            logger.error(f"Error from connection {err}")
            raise ConnectionExecption(message=f"Error from connection", err=err, url=self.host)
