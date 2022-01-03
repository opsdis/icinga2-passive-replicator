# Passive check result
curl -k -s -S -i -u root:3685763dc546a77d -H 'Accept: application/json' \
-X POST 'http://172.25.1.64:5665/v1/actions/process-check-result' \
-d '{ "type": "Service", "filter": "host.name==\"www.sunet.se\" && service.name==\"ping4\"", "exit_status": 2, "plugin_output": "PING CRITICAL - Packet loss = 100%", "performance_data": [ "rta=5000.000000ms;3000.000000;5000.000000;0.000000", "pl=100%;80;100;0" ], "check_source": "example.localdomain", "pretty": true }'


# Crete host object
curl -k -s -S -i -u root:3685763dc546a77d -H 'Accept: application/json' \
-X PUT 'https://172.25.1.64:5665/v1/objects/hosts/megatexc1' \
-d '{ "templates": [ "generic-host" ], "attrs": { "address": "192.168.1.1", "check_command": "dummy", "enable_active_checks": false, "vars.os" : "Linux" }, "pretty": true }'

curl -k -s -S -i -u root:3685763dc546a77d -H 'Accept: application/json' \
-X PUT 'https://172.25.1.64:5665/v1/objects/hosts/megatexc1' \
-d '{ "attrs": { "address": "192.168.1.1", "check_command": "dummy", "enable_active_checks": false, "vars.os" : "Linux" }, "pretty": true }'


# Delete host with cascade
curl -k -s -S -i -u root:3685763dc546a77d -H 'Accept: application/json'  -X DELETE 'https://172.25.1.64:5665/v1/objects/hosts/megatexc1?cascade=1' 

# query service and host
curl -k -s   -u root:3685763dc546a77d -H 'Accept: application/json' -H 'X-HTTP-Method-Override: GET' -d '{ "type": "Service", "filter": "\"all_host_group\" in host.groups" }' -X POST 'https://localhost:5665/v1/objects/services?joins=host' | jq . | less

# query service and join host.name
curl -k -s   -u root:3685763dc546a77d -H 'Accept: application/json' -H 'X-HTTP-Method-Override: GET' -d '{ "type": "Service", "filter": "\"all_host_group\" in host.groups" }' -X POST 'https://localhost:5665/v1/objects/services?joins=host.name&attrs=display_name&attrs=last_check_result&attrs=vars' | jq . | less

curl -k -s   -u root:3685763dc546a77d -H 'Accept: application/json' -H 'X-HTTP-Method-Override: GET' -d '{ "type": "Service", "filter": "\"all_host_group\" in host.groups", "joins": ["host.name"], "attrs": ["display_name", "last_check_result", "vars"] }' -X POST 'https://localhost:5665/v1/objects/services' | jq . | less

# query host
curl -k -s   -u root:3685763dc546a77d -H 'Accept: application/json' -H 'X-HTTP-Method-Override: GET' -d '{ "type": "Host", "filter": "\"all_host_group\" in host.groups", "attrs": ["name", "last_check_result", "vars"] }' -X POST 'https://localhost:5665/v1/objects/hosts' | jq . | less