# redpanda_console

Installs and configures Redpanda Console from the package repositories
(stable or unstable channel), rendering the configuration that matches
the installed console major version. Configuration merges the `rpconsole`
variable into the defaults; the rendered file is owned by the console
user and not world-readable (it can carry SASL/login secrets).

Use as `redpanda.cluster.redpanda_console`.

## TLS migration note

Console 3.x reads TLS material as the `redpanda_console` user; existing
deployments upgrading from 2.x get certificate ownership migrated by the
role (see `tasks/migrate-ownership.yml`).

## Variables

The load-bearing inputs are validated by `meta/argument_specs.yml` and
documented below; any further tunables live in `defaults/main.yml`.

<!-- BEGIN ROLE VARIABLES (generated from meta/argument_specs.yml; run scripts/generate-role-docs.py) -->

| Variable | Type | Default | Choices | Description |
|---|---|---|---|---|
| `redpanda_version` | str | `latest` | — | C o n s o l e   v e r s i o n   t o   i n s t a l l ,   o r   l a t e s t . |
| `enable_airgap` | bool | `False` | — |  |
| `handle_cert_install` | bool | `False` | — |  |
| `install_certs_only` | bool | `False` | — |  |
| `is_using_unstable` | bool | `False` | — |  |
| `redpanda_console_user` | str | `redpanda_console` | — |  |
| `redpanda_console_group` | str | `redpanda_console` | — |  |

Variables not listed here are undeclared in the argument spec; see `defaults/main.yml`.

<!-- END ROLE VARIABLES -->
