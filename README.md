[![Python application](https://github.com/opsdis/icinga2-passive-replicator/actions/workflows/python-app.yml/badge.svg)](https://github.com/opsdis/icinga2-passive-replicator/actions/workflows/python-app.yml)

icinga2-passive-replicator
--------------------------

# Overview
The icinga2-passive-replicator, or for short `i2pr`, is a simple solution to replicate state and performance
data for hosts and service from one Icinga2 instance, source, to another instance, sink.

The solution will scrape the source Icinga2 instance on a regular interval of 60 seconds. 
The scraping is done for all hosts and services that belong to a number of specified hostgroups.
Which hostgroups to scrape is specified with the environment variable `I2PR_SOURCE_HOSTGROUPS`, e.g.

    I2PR_SOURCE_HOSTGROUPS="Ubuntu, Mysql"

The above will scrape all hosts and services in the hostgroups `Ubuntu` and `Mysql`.

If a host or service does not exist in the sink instance it will be created.
The objects will be created with the templates. Default for hosts is `generic-host`
and for services is `generic-service`.

Default check command will be `dummy`.

Created host and service will always have a variable called `i2pr` set to `true` and be added to hostgroup(s) 
defined in the environment variable `I2PR_SINK_HOSTGROUPS`, default is `i2pr`.

All existing variables on the object will be created, but with a prefix default to `i2pr_`.

Check out the `.example_env` file for configuration options. For the options to take effect please
rename the file to `.env` or set the options as environment variables.

> If a host/service exists on the source, but have never been executed there will be no state or performance data.
In this case the host/service will not be replicated until it have been executed for the first time.

> If a host on the source have a state except 0 (UP) or 1 (DOWN), like 2 or 3 the state will on the sink be set 
to 1. This is due to the passive check API for a host only accept 0 or 1.

# Run i2pr
Edit the `.env` and `logging.conf` files according to your setup. Please check out `.example_env` for configuration of
the `.env` file.

```bash
python3 -m venv venv
. venv/bin/activate
pip install -r requierments.txt
python -m icinga2_passive_replicator
```

# Run i2pr as a service
Checkout the example in `scripts/i2pr.service`. The script expect that i2pr is installed in /opt as 
`/opt/i2pr`.

# Run i2pr as a docker

Build the docker image

    docker build -t icinga2_passive_replicator .

Run the image with mount volumes for configuration

    docker run -v $(pwd)/.env:/app/.env -v $(pwd)/logging.conf:/app/logging.conf icinga2_passive_replicator

# Monitor i2pr
The service expose the following endpoint:

- `/health` return http status 200 if okay or 503 if not
- `/metrics` return the internal metrics, default i prometheus format. Using query parameter `format=json` the
output will be json formatted