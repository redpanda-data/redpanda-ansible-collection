# Ansible Collection for Redpanda

`redpanda.cluster` provisions and manages self-hosted [Redpanda](https://www.redpanda.com/) clusters: brokers, Redpanda Console, Kafka Connect, TLS material, OS preparation, and SASL user/ACL management.

- Documentation: [production deployment automation](https://docs.redpanda.com/current/deploy/deployment-option/self-hosted/manual/production/production-deployment-automation/)
- Example playbooks and end-to-end harness: [deployment-automation](https://github.com/redpanda-data/deployment-automation)
- Issues: [redpanda-ansible-collection](https://github.com/redpanda-data/redpanda-ansible-collection/issues)

## Installation

```shell
ansible-galaxy collection install redpanda.cluster
```

Requires ansible-core >= 2.18. The collection declares its dependencies (`community.general`, `ansible.posix`), which ansible-galaxy installs automatically.

## Roles

| Role | Purpose |
|---|---|
| `redpanda.cluster.system_setup` | OS preparation: data volume discovery/mount, prerequisite packages, redpanda user |
| `redpanda.cluster.sysctl_setup` | Kernel tuning (aio-max-nr, panic behavior) |
| `redpanda.cluster.redpanda_broker` | Install and configure brokers, TLS/SASL/tiered storage, safe rolling restarts |
| `redpanda.cluster.redpanda_console` | Install and configure Redpanda Console |
| `redpanda.cluster.redpanda_connect` | Install and configure Kafka Connect (Fedora/RHEL-family hosts) |
| `redpanda.cluster.redpanda_logging` | rsyslog/logrotate/journald configuration for broker logs |
| `redpanda.cluster.user_management` | Declarative SASL users, roles, and ACLs via rpk |
| `redpanda.cluster.client_config` | Install rpk and client certificates on client hosts |
| `redpanda.cluster.demo_certs` | Demo-only local CA, node certs, and truststore (not for production) |
| `redpanda.cluster.binary_bundler` | Build package tarballs for airgapped installs |

Each role's README documents its variables. A minimal play:

```yaml
- hosts: redpanda
  become: true
  roles:
    - redpanda.cluster.system_setup
    - redpanda.cluster.sysctl_setup
    - redpanda.cluster.redpanda_broker
  vars:
    redpanda_version: latest
```

Hosts in the `redpanda` inventory group need a `private_ip` hostvar (the address brokers advertise to each other).

## SASL Authentication

```yaml
kafka_enable_authorization: true
sasl_superuser_username: "admin"
sasl_superuser_password: "secure-password"

schema_registry_service_user: "schema_registry_client"
schema_registry_service_password: "secure-password"
pandaproxy_service_user: "pandaproxy_client"
pandaproxy_service_password: "secure-password"
```

Mixed authentication (internal no-auth, external SASL):

```yaml
redpanda_kafka_listeners:
  - address: "{{ private_ip }}"
    port: 9092
    name: "internal"
    authentication_method: "none"
  - address: "0.0.0.0"
    port: 9093
    name: "external"
    authentication_method: "sasl"
```

Enterprise features (requires license):

```yaml
schema_registry_enable_authorization: true
redpanda_license_file: "{{ playbook_dir }}/redpanda.license"
admin_api_require_auth: true
```

See the `user_management` role for managing users and ACLs.

## Development

Each role carries a containerized test suite: `cd roles/<role> && docker compose run --rm testctr make do`. Collection-level packaging tests run from the root with `python3 -m pytest tests/packaging/`. Lint with `make lint`.

Changelog fragments (antsibull-changelog) are expected with changes; see `changelogs/fragments/`.

### Releasing

Bump `version` in `galaxy.yml` (repo root), generate the changelog, then build and publish:

```shell
antsibull-changelog release --version <version>
ansible-galaxy collection build
ansible-galaxy collection publish redpanda-cluster-*.tar.gz --token <YOUR_API_KEY> -s https://galaxy.ansible.com/api/
```

Publishing requires [permissions on the Galaxy namespace](https://galaxy.ansible.com/ui/namespaces/redpanda/).

## Troubleshooting

### On Mac OS X, Python unable to fork workers

If you see something like this:

```
ok: [34.209.26.177] => {“changed”: false, “stat”: {“exists”: false}}
objc[57889]: +[__NSCFConstantString initialize] may have been in progress in another thread when fork() was called.
ERROR! A worker was found in a dead state
```

You might try resolving by setting an environment variable:
`export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`

See: https://stackoverflow.com/questions/50168647/multiprocessing-causes-python-to-crash-and-gives-an-error-may-have-been-in-progr
