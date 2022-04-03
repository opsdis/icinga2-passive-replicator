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
from typing import Dict, Any
import urllib3
from icinga2_passive_replicator.connection import ConnectionException, SourceException

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class Source:

    def __init__(self):
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
        try:
            body = {
                "type": "Host",
                "attrs": ["name", "display_name", "last_check_result", "vars"],
                "filter": '\"{}\" in host.groups'.format(self.hostgroup)
            }

            data_json = self._post(self.url_query_hosts, body)
        except ConnectionException as err:
            raise SourceException(err)

        return data_json

    def get_service_data(self) -> Dict[str, Any]:
        """
        Get service data
        :return:
        """
        try:
            body = {
                "type": "Service",
                "joins": ["host.name"],
                "attrs": ["display_name", "last_check_result", "vars"],
                "filter": '\"{}\" in host.groups'.format(self.hostgroup)
            }

            data_json = self._post(self.url_query_services, body)
        except ConnectionException as err:
            raise SourceException(err)
        return data_json

    def _post(self, url, body=None) -> Dict[str, Any]:
        """
        Do a post request to Icinga source
        :param url:
        :param body:
        :return:
        """
        logger.debug(f"message=\"Request source\" body=\"{body}\"")
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
                    logger.info(f"message=\"Call source\" host={self.host} method=post "
                                f"url={url} status={response.status_code} "
                                f"response_time={time.monotonic() - start_time}")

                    if response.status_code != 200 and response.status_code != 201:
                        logger.warning(f"message=\"{response.reason}\" status={response.status_code}")
                        raise ConnectionException(message=f"Http status {response.status_code}", err=None,
                                                  url=self.host)
                    # logger.debug(f"message=\"Response source\" payload=\"{response.text}\"")
                    try:
                        return json.loads(response.text)
                    except Exception as err:
                        # Remove after debug - just to catch it
                        logger.warning(f"message=\"Response could not be parsed from json\" error={err}")
                        return json.loads(response.text)

        except requests.exceptions.RequestException as err:
            logger.error(f"message=\"Error from connection\" error=\"{err}\"")
            raise ConnectionException(message=f"Error from connection", err=err, url=self.host)
