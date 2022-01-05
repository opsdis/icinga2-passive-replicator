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
The objects will be created with the with templates. Default for hosts is `generic-host`
and for services is `generic-service`.
Default check command will be `dummy`.
Created host and service will always have a variable called `i2pr` set to `true`.
All existing variables on the object will be created, but with a prefix default to `i2pr_`.

Check out the `.example_env` file for configuration options. For the options to take effect please
rename the file to `.env` or set the options as environment variables.

# Run i2pr
Edit the `.env` and `logging.conf` files according to your setup. Please checkout `.example_env` for configuration of
the `.env` file.


```bash
python3 -m venv venv
. venv/bin/activate
pip install -r requierments.txt
python -m icinga2_passive_replicator

```

# Run i2pr as a service
Checkout the example in `scripts/i2pr.service`

# Monitor i2pr
The service expose the following endpoint:

- `/health` return http status 200 if okay or 503 if not
- `/metrics` return the internal metrics, default i prometheus format. Using query paramater `format=json` the
output will be json formatted