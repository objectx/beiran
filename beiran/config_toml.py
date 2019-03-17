config_yaml = """
# beiran configuration file

# general settings which is valid all parts, lib, daemon and all plugins
[beiran]
log_level = 'DEBUG'
log_file = '/var/log/beirand.log'
config_dir = '/etc/beiran'
data_dir = '/var/lib/beiran'
run_dir = '/var/run'
listen_port = 8888
listen_address = '0.0.0.0'
socket_file = '/var/run/beirand.sock'
discovery_method = 'zeroconf'

# docker plugin settings
[package.docker]
enabled = true
cache_dir = '/var/cache/beiran/docker'
module_path = 'beiran_package_docker'

# dns discovery settings
[discovery.dns]
enabled = true
module_path = 'beiran.plugins.discovery_dns'

# zeroconf discovery settings
[discovery.zeroconf]
enabled = true
module_path = 'beiran.plugins.discovery_zeroconf'
"""