# redpanda_connect

Installs and configures Kafka Connect for Redpanda on RHEL-family hosts.
The RPM must either be pre-staged at `connect_rpm_location` or fetched
via `connect_rpm_url` (optionally verified with `connect_rpm_checksum`);
Debian hosts are not supported for installation. Configuration files
(connect-distributed properties, log4j, JMX exporter, systemd unit) are
generated from templates and can be replaced wholesale via the
`*_override_content` variables documented in `defaults/main.yml`; config
changes trigger a safe restart with a REST health check.

Use as `redpanda.cluster.redpanda_connect` against the `connect`
inventory group.

## Variables

The load-bearing inputs are validated by `meta/argument_specs.yml` and
documented below; any further tunables live in `defaults/main.yml`.

<!-- BEGIN ROLE VARIABLES (generated from meta/argument_specs.yml; run scripts/generate-role-docs.py) -->

| Variable | Type | Default | Choices | Description |
|---|---|---|---|---|
| `restart_only` | bool | `False` | — |  |
| `use_existing_jvm` | bool | `False` | — |  |
| `copy_keystore` | bool | `False` | — |  |
| `copy_truststore` | bool | `False` | — |  |
| `connect_distributed_config_file` | str | `connect-distributed.properties` | — |  |
| `connect_rpm_url` | str | — | — | O p t i o n a l   U R L   t o   d o w n l o a d   t h e   C o n n e c t   R P M   f r o m . |
| `connect_rpm_checksum` | str | — | — | O p t i o n a l   c h e c k s u m   ( e . g .   s h a 2 5 6 : < h e x > )   f o r   t h e   R P M   d o w n l o a d . |

Variables not listed here are undeclared in the argument spec; see `defaults/main.yml`.

<!-- END ROLE VARIABLES -->
