# redpanda_broker

Installs and configures Redpanda brokers: package installation (stable,
unstable, nightly, or airgap bundles), node and cluster configuration
(TLS, SASL, tiered storage, FIPS), enterprise license application, and
safe rolling restarts when configuration changes require them.

Use as `redpanda.cluster.redpanda_broker`. Hosts must be in the `redpanda`
inventory group and carry a `private_ip` hostvar.

## Behavior

- Configuration is merged from the built-in templates plus the free-form
  `redpanda` variable (cluster/node overrides) and `host_specific_override`.
- On clusters that are already initialized, config changes that require a
  restart trigger a serial rolling restart: maintenance mode on, restart,
  wait for the admin API and `rpk cluster health` to report healthy, then
  maintenance mode off. Set `restart_node: false` to opt out.
- With `kafka_enable_authorization: true` on first bootstrap, the
  superuser is created via `/etc/redpanda.d/bootstrap-superuser.conf`
  (removed after the run) and Schema Registry / Pandaproxy service
  accounts are created.

## Variables

The load-bearing inputs are validated by `meta/argument_specs.yml` and
documented below; the full set of tunables lives in `defaults/main.yml`.

<!-- BEGIN ROLE VARIABLES (generated from meta/argument_specs.yml; run scripts/generate-role-docs.py) -->

| Variable | Type | Default | Choices | Description |
|---|---|---|---|---|
| `redpanda_version` | str | `latest` | — | Redpanda version to install (e.g. `24.3.1-1`` or `latest`. |
| `redpanda_install_status` | str | `present` | `present`, `latest` | `latest` upgrades an existing install when redpanda_version is `latest`; `present` leaves an installed version alone. |
| `fips_mode` | str | `disabled` | `disabled`, `permissive`, `enabled` | Redpanda FIPS mode. `enabled` requires the OS to have FIPS correctly enabled. |
| `enable_fips` | bool | `False` | — |  |
| `enable_tls` | bool | `False` | — |  |
| `require_client_auth` | bool | `False` | — |  |
| `kafka_enable_authorization` | bool | `False` | — | Enables SASL authorization; requires sasl_superuser_username and sasl_superuser_password. |
| `sasl_superuser_username` | str | `admin` | — |  |
| `sasl_superuser_password` | str | `change-me-in-production` | — |  |
| `restart_node` | bool | `True` | — | Set to false to manage broker restarts yourself. |
| `handle_cert_install` | bool | `False` | — |  |
| `install_certs_only` | bool | `False` | — |  |
| `enable_airgap` | bool | `False` | — |  |
| `development_build` | bool | `False` | — |  |
| `is_using_unstable` | bool | `False` | — |  |
| `redpanda_config_file_mode` | str | `0640` | — |  |
| `redpanda_kafka_listeners` | list of dict | — | — | Kafka API listeners; each entry needs address, port and name. |

Variables not listed here are undeclared in the argument spec; see `defaults/main.yml`.

<!-- END ROLE VARIABLES -->

## Secrets handling

Passwords are passed to rpk via environment variables, never argv. Note
that Ansible inlines task environments into the connection exec line, so
`-vvv` output exposes them regardless of `no_log` — treat verbose CI logs
as sensitive. `redpanda.yaml` and `.bootstrap.yaml` default to mode 0640
(`redpanda_config_file_mode`).

## Testing

`cd roles/redpanda_broker && docker compose run --rm testctr make do`
runs the containerized suite (template renders, real task files driven
with mocked rpk, shellcheck, bats).
