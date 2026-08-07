# client_config

Installs the rpk CLI and the client truststore on client hosts. rpk
downloads from the official releases by default; point `rpk_base_url` at
a mirror, pin `rpk_version`, or override the full `rpk_url`, optionally
verifying `rpk_checksum`. The CA certificate is copied from
`cert_src_dir` to `cert_dest_dir`.

Use as `redpanda.cluster.client_config`.

## Variables

The load-bearing inputs are validated by `meta/argument_specs.yml` and
documented below; any further tunables live in `defaults/main.yml`.

<!-- BEGIN ROLE VARIABLES (generated from meta/argument_specs.yml; run scripts/generate-role-docs.py) -->

| Variable | Type | Default | Choices | Description |
|---|---|---|---|---|
| `rpk_base_url` | str | `https://github.com/redpanda-data/redpanda/releases` | — |  |
| `rpk_version` | str | `latest` | — |  |
| `rpk_url` | str | — | — | F u l l   d o w n l o a d   U R L   o v e r r i d e ;   w i n s   o v e r   b a s e / v e r s i o n . |
| `rpk_checksum` | str | — | — | O p t i o n a l   c h e c k s u m   ( e . g .   s h a 2 5 6 : < h e x > )   f o r   t h e   d o w n l o a d . |
| `cert_dest_dir` | str | `/opt/rpk/certs` | — |  |
| `truststore_name` | str | `ca.crt` | — |  |

Variables not listed here are undeclared in the argument spec; see `defaults/main.yml`.

<!-- END ROLE VARIABLES -->
