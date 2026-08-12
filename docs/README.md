# redpanda.cluster documentation

The authoritative usage guide for this collection is the
[production deployment automation](https://docs.redpanda.com/current/deploy/deployment-option/self-hosted/manual/production/production-deployment-automation/)
documentation, with runnable example playbooks in the
[deployment-automation](https://github.com/redpanda-data/deployment-automation)
repository.

Per-role variable documentation lives in each role's README:

- [system_setup](../roles/system_setup/README.md)
- [sysctl_setup](../roles/sysctl_setup/README.md)
- [redpanda_broker](../roles/redpanda_broker/README.md)
- [redpanda_console](../roles/redpanda_console/README.md)
- [redpanda_connect](../roles/redpanda_connect/README.md)
- [redpanda_logging](../roles/redpanda_logging/README.md)
- [user_management](../roles/user_management/README.md)
- [client_config](../roles/client_config/README.md)
- [demo_certs](../roles/demo_certs/README.md)
- [binary_bundler](../roles/binary_bundler/README.md)

Roles that validate their inputs declare them in
`roles/<role>/meta/argument_specs.yml`; those specs are the source of truth
for types, defaults, and allowed values.

## Behavior worth knowing

- Re-running the broker role against a live cluster performs a safe rolling
  restart when configuration changes require one: each node is drained into
  maintenance mode, restarted, and must report `Healthy: true` via
  `rpk cluster health` before the next node is touched. Set
  `restart_node: false` to manage restarts yourself.
- The play re-asserts the configuration it is given: if you enabled TLS in a
  previous run, subsequent runs must keep the same TLS variables or the
  cluster configuration will be rewritten without them.
- Hosts in the `redpanda` group need a `private_ip` hostvar; brokers
  advertise it to each other.
