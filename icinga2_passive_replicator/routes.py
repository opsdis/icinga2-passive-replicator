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

import logging
import os
import time
from typing import Dict, Any, Tuple

import uvicorn
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse, Response
from fastapi_utils.tasks import repeat_every
from pydantic import BaseSettings

from icinga2_passive_replicator.connection import ConnectionException, SinkException, SourceException
from icinga2_passive_replicator.containers import Hosts, Services, Host, Service
from icinga2_passive_replicator.sink_connection import Sink
from icinga2_passive_replicator.source_connection import Source

TEST_PREFIX = ''

logging.config.fileConfig(os.getenv('I2PR_LOGGING_CONFIG', './logging.conf'), disable_existing_loggers=False)

logger = logging.getLogger(__name__)


class MissingLastCheckResult(Exception):
    pass


class Settings(BaseSettings):
    i2pr_source_host: str = 'https://localhost:5665'
    i2pr_source_user: str = 'root'
    i2pr_source_passwd: str = ''
    i2pr_source_hostgroups = ''

    i2pr_sink_host: str = 'https://localhost:5665'
    i2pr_sink_user: str = 'root'
    i2pr_sink_passwd: str = ''
    i2pr_sink_vars_prefix = 'i2pr_'
    i2pr_sink_host_template = 'generic-host'
    i2pr_sink_service_template = 'generic-service'
    i2pr_sink_check_command = 'dummy'
    i2pr_sink_hostgroups = 'i2pr'

    class Config:
        env_file = ".env"


class Status:
    def __init__(self):

        self.health = True
        self.scrapes_total = 0
        self.push_total = 0
        self.passive_checks_total = 0
        self.failed_scrapes_total = 0
        self.failed_push_total = 0
        self.scrape_time_seconds_total = 0.0
        self.push_time_seconds_total = 0.0

    def inc_scrapes(self):
        self.scrapes_total += 1

    def inc_failed_scrapes(self):
        self.failed_scrapes_total += 1

    def inc_push(self):
        self.push_total += 1

    def inc_failed_push(self):
        self.failed_push_total += 1

    def inc_total_passive_checks(self, value):
        self.passive_checks_total += value

    def get_health(self) -> bool:
        return self.health

    def healthy(self):
        self.health = True

    def unhealthy(self):
        self.health = False

    def inc_scrape_time(self, value: float):
        self.scrape_time_seconds_total += value

    def inc_push_time(self, value: float):
        self.push_time_seconds_total += value

    def to_dict(self) -> Dict[str, Any]:
        filtered = {}
        for key, value in self.__dict__.items():
            if key[0] != '_':
                if isinstance(value, bool):
                    filtered[key] = int(value)
                else:
                    filtered[key] = value
        filtered['avg_passive_checks'] = self.passive_checks_total / self.push_total
        filtered['avg_scrape_time_seconds'] = self.scrape_time_seconds_total / self.scrapes_total
        filtered['avg_push_time_seconds'] = self.push_time_seconds_total / self.push_total
        return filtered

    def to_prometheus(self) -> str:
        new_line = '\n'
        prom_output = ''
        for key, value in self.__dict__.items():
            if key[0] != '_':
                if isinstance(value, bool):
                    prom_output += f"{key} {int(value)}{new_line}"
                else:
                    prom_output += f"{key} {value}{new_line}"
        return prom_output


health = Status()

settings = Settings()
app = FastAPI()


@app.get("/health")
async def healthz():
    if health.get_health():
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "okay"})
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "failed"})


@app.get("/metrics")
async def metrics(metric_format: str = 'prometheus'):
    if metric_format == 'prometheus':
        return Response(content=health.to_prometheus(), media_type="text/html", status_code=status.HTTP_200_OK)
    if metric_format == 'json':
        return JSONResponse(content=health.to_dict(), status_code=status.HTTP_200_OK)
    return Response(content=health.to_prometheus(), media_type="text/html", status_code=status.HTTP_200_OK)


@app.on_event("startup")
def validate_sink_preconditions() -> None:
    sink = Sink()
    sink.host = settings.i2pr_sink_host
    sink.user = settings.i2pr_sink_user
    sink.passwd = settings.i2pr_sink_passwd
    sink.host_template = settings.i2pr_sink_host_template
    sink.service_template = settings.i2pr_sink_service_template
    sink.hostgroups = [s.strip() for s in settings.i2pr_sink_hostgroups.split(',')]

    sink.validate_preconditions()


@app.on_event("startup")
@repeat_every(seconds=60)
def process_replication() -> None:
    try:
        for hostgroup in settings.i2pr_source_hostgroups.split(","):
            start_time = time.monotonic()
            hosts, services = collect_from_source(hostgroup.strip())
            health.inc_scrapes()
            process_time = time.monotonic() - start_time
            health.inc_scrape_time(process_time)
            logger.info(f"message=\"Process scrape\" hostgroup=\"{hostgroup.strip()}\" "
                        f"response_time={process_time}")

            start_time = time.monotonic()
            total_passive_checks = push_to_sink(hosts, services)
            health.inc_total_passive_checks(total_passive_checks)
            health.inc_push()
            process_time = time.monotonic() - start_time
            health.inc_push_time(process_time)

            logger.info(f"message=\"Process push\" hostgroup=\"{hostgroup.strip()}\" "
                        f"total_passive_checks={total_passive_checks} response_time={process_time}")
        health.healthy()
    except SinkException:
        health.unhealthy()
        health.inc_failed_push()
    except SourceException:
        health.unhealthy()
        health.inc_failed_scrapes()
    except Exception as err:
        # Catch all and exit - unexpected exception
        logger.error(f"message=\"Unexpected exception - exit\" error\"{err}\"")
        exit(-1)


def collect_from_source(hostgroup: str) -> Tuple[Hosts, Services]:
    logger.debug(f"message=\"Collect from source icinga2 instance\"")

    source = Source()
    source.host = settings.i2pr_source_host
    source.user = settings.i2pr_source_user
    source.passwd = settings.i2pr_source_passwd
    source.hostgroup = hostgroup

    hosts = Hosts()
    try:
        host_data = source.get_host_data()
        # To use when debugging another systems data
        # with open('cc.json') as json_file:
        #    host_data = json.load(json_file)

        if 'results' not in host_data:
            logger.debug(f"message=\"The results attribute is not in host_data\"")
        for item in host_data['results']:
            try:
                icinga_host = create_host(item)
            except MissingLastCheckResult:
                # Do not add host if missing check result
                continue
            hosts.add(icinga_host)
    except ConnectionException as err:
        logger.warning(f"message=\"Received no host data from source Icinga2\" error=\"{err}\"")
        raise err

    services = Services()
    try:
        service_data = source.get_service_data()
        if 'results' not in service_data:
            logger.warning(f"message=\"The results attribute is not in service_data\"")

        for item in service_data['results']:
            try:
                icinga_service = create_service(item)
            except MissingLastCheckResult:
                # Do not add service if missing check result
                continue

            services.add(icinga_service)
    except ConnectionException as err:
        logger.warning(f"message=\"Received no service data from source Icinga2\" error=\"{err}\"")
        raise err

    return hosts, services


def push_to_sink(hosts: Hosts, services: Services) -> int:
    sink = Sink()
    sink.host = settings.i2pr_sink_host
    sink.user = settings.i2pr_sink_user
    sink.passwd = settings.i2pr_sink_passwd
    sink.vars_prefix = settings.i2pr_sink_vars_prefix
    sink.host_template = settings.i2pr_sink_host_template
    sink.service_template = settings.i2pr_sink_service_template
    sink.check_command = settings.i2pr_sink_check_command
    sink.hostgroups = [s.strip() for s in settings.i2pr_sink_hostgroups.split(',')]

    count_passive_checks = sink.push(hosts)
    count_passive_checks += sink.push(services)

    return count_passive_checks


def create_host(item: Dict[str, Any]) -> Host:
    logger.debug(f"message=\"Host item\" item=\"{item}\"")
    host = Host()
    host.name = f"{TEST_PREFIX}{item['name']}"
    host.display_name = item['attrs']['display_name']
    if item['attrs']['last_check_result']:
        host.exit_status = item['attrs']['last_check_result']['exit_status']
        # For the passive check API for a host the only allowed values are 0 (UP) or 1 (DOWN)
        if host.exit_status > 1:
            logger.info(
                f"message=\"Invalid host exit status - will set to 1 (DOWN)\" host=\"{host.name}\" "
                f"exit_status={host.exit_status}")
            host.exit_status = 1

        host.performance_data = item['attrs']['last_check_result']['performance_data']
        output = str(item['attrs']['last_check_result']['output'])
        host.output = output.strip().replace('\n', ' ')
    else:
        logger.warning(f"message=\"The host is missing last_check_result\" host=\"{host.name}\"")
        raise MissingLastCheckResult()

    host.vars = item['attrs']['vars']
    return host


def create_service(item: Dict[str, Any]) -> Service:
    service = Service()
    service.host_name = item['joins']['host']['name']

    service.name = f"{TEST_PREFIX}{item['name']}"
    service.display_name = item['attrs']['display_name']
    if item['attrs']['last_check_result']:
        service.exit_status = item['attrs']['last_check_result']['exit_status']
        service.performance_data = item['attrs']['last_check_result']['performance_data']
        output = str(item['attrs']['last_check_result']['output'])
        service.output = output.strip().replace('\n', ' ')
    else:
        logger.warning(
            f"message=\"The service is missing last_check_result\" host=\"{service.host_name}\" "
            f"service=\"{service.name}\"")
        raise MissingLastCheckResult()

    service.vars = item['attrs']['vars']
    return service


def startup():
    logging.config.fileConfig(os.getenv('I2PR_LOGGING_CONFIG', './logging.conf'), disable_existing_loggers=False)
    # init(os.getenv('I2PR_TENANT_CONFIG', "./config.yml"))
    uvicorn.run(app, host=os.getenv('I2PR_HOST', "0.0.0.0"), port=os.getenv('I2PR_PORT', 5010))
