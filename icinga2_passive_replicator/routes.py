import os
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

import logging
from fastapi_utils.tasks import repeat_every

from icinga2_passive_replicator.connection import ConnectionException, SinkException, SourceException
from icinga2_passive_replicator.containers import Hosts, Services, Host, Service
from icinga2_passive_replicator.sink_connection import Sink
from icinga2_passive_replicator.source_connection import Source
from pydantic import BaseSettings

TEST_PREFIX = ''

logging.config.fileConfig(os.getenv('I2PR_LOGGING_CONFIG', './logging.conf'), disable_existing_loggers=False)

logger = logging.getLogger(__name__)


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

    class Config:
        env_file = ".env"


class Status:
    def __init__(self):
        self.health = True
        self.total_scrapes = 0
        self.total_push = 0
        self.failed_scrapes = 0
        self.failed_push = 0

    def inc_scrapes(self):
        self.total_scrapes += 1

    def inc_failed_scrapes(self):
        self.failed_scrapes += 1

    def inc_push(self):
        self.total_push += 1

    def inc_failed_push(self):
        self.failed_push += 1

    def get_health(self) -> bool:
        return self.health

    def healthy(self):
        self.health = True

    def unhealthy(self):
        self.health = False


health = Status()

settings = Settings()
app = FastAPI()


@app.get("/health")
async def healthz():
    if health.get_health():
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "okay"})
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "failed"})


@app.get("/metrics")
async def metrics():
    return health


@app.on_event("startup")
@repeat_every(seconds=60)
def process_replication() -> None:
    try:
        for hostgroup in settings.i2pr_source_hostgroups.split(","):
            logger.info(f"message=\"Collect and push for hostgroup\" hostgroup=\"{hostgroup.strip()}\"")
            hosts, services = collect_from_source(hostgroup.strip())
            health.inc_scrapes()
            push_to_sink(hosts, services)
            health.inc_push()
        health.healthy()
    except SinkException:
        health.unhealthy()
        health.inc_failed_push()
    except SourceException:
        health.unhealthy()
        health.inc_failed_scrapes()


def collect_from_source(hostgroup: str):
    logger.debug(f"message=\"Collect from source icinga2 instance\"")

    source = Source()
    source.host = settings.i2pr_source_host
    source.user = settings.i2pr_source_user
    source.passwd = settings.i2pr_source_passwd
    source.hostgroup = hostgroup

    hosts = Hosts()
    try:
        host_data = source.get_host_data()
        for item in host_data['results']:
            icinga = create_host(item)
            hosts.add(icinga)
    except ConnectionException as err:
        logger.warning(f"message=\"Received no host data from source Icinga2\" error=\"{err}\"")
        raise err

    services = Services()
    try:
        service_data = source.get_service_data()
        for item in service_data['results']:
            icinga = create_service(item)
            services.add(icinga)
    except ConnectionException as err:
        logger.warning(f"message=\"Received no service data from source Icinga2\" error=\"{err}\"")
        raise err

    return hosts, services


def push_to_sink(hosts: Hosts, services: Services):
    sink = Sink()
    sink.host = settings.i2pr_sink_host
    sink.user = settings.i2pr_sink_user
    sink.passwd = settings.i2pr_sink_passwd
    sink.vars_prefix = settings.i2pr_sink_vars_prefix
    sink.host_template = settings.i2pr_sink_host_template
    sink.service_template = settings.i2pr_sink_service_template
    sink.check_command = settings.i2pr_sink_check_command

    sink.push(hosts)
    sink.push(services)


def create_host(item: Dict[str, Any]) -> Host:
    host = Host()
    host.name = f"{TEST_PREFIX}{item['name']}"
    host.exit_status = item['attrs']['last_check_result']['exit_status']
    host.performance_data = item['attrs']['last_check_result']['performance_data']
    host.output = item['attrs']['last_check_result']['output']
    host.vars = item['attrs']['vars']
    return host


def create_service(item: Dict[str, Any]) -> Service:
    service = Service()
    service.host_name = item['joins']['host']['name']
    service.display_name = item['attrs']['display_name']
    service.name = f"{TEST_PREFIX}{item['name']}"
    service.exit_status = item['attrs']['last_check_result']['exit_status']
    service.performance_data = item['attrs']['last_check_result']['performance_data']
    service.output = item['attrs']['last_check_result']['output']
    service.vars = item['attrs']['vars']
    return service


def startup():
    logging.config.fileConfig(os.getenv('I2PR_LOGGING_CONFIG', './logging.conf'), disable_existing_loggers=False)
    # init(os.getenv('I2PR_TENANT_CONFIG', "./config.yml"))
    uvicorn.run(app, host=os.getenv('I2PR_HOST', "0.0.0.0"), port=os.getenv('I2PR_PORT', 5010))


if __name__ == "__main__":
    logging.config.fileConfig(os.getenv('I2PR_LOGGING_CONFIG', './logging.conf'), disable_existing_loggers=False)
    # init(os.getenv('I2PR_TENANT_CONFIG', "../tenant_config.yml"))
    uvicorn.run(app, host="0.0.0.0", port=5010)
