# demo_certs

Creates a throwaway local CA on the control node, issues node
certificates for the play hosts, and optionally builds a Java truststore
for the connect group. **Demo use only — not for production**: the CA
key lives unencrypted on the control node and default store passwords
are placeholders.

Use as `redpanda.cluster.demo_certs` with `create_demo_certs: true`
(and `create_keystore: true` for the truststore). Artifacts land under
`tls/` relative to the playbook directory (`root_ca_dir` for the CA).
Keystore generation itself is owned by the `redpanda_connect` role.

## Variables

The load-bearing inputs are validated by `meta/argument_specs.yml` and
documented below; any further tunables live in `defaults/main.yml`.

<!-- BEGIN ROLE VARIABLES (generated from meta/argument_specs.yml; run scripts/generate-role-docs.py) -->

| Variable | Type | Default | Choices | Description |
|---|---|---|---|---|
| `create_demo_certs` | bool | `False` | — | C r e a t e   t h e   d e m o   C A   a n d   i s s u e   n o d e   c e r t i f i c a t e s . |
| `create_keystore` | bool | `False` | — | G e n e r a t e   t h e   J a v a   t r u s t s t o r e   f o r   t h e   c o n n e c t   g r o u p . |
| `root_ca_dir` | str | `tls/ca` | — | C o n t r o l - s i d e   d i r e c t o r y   h o l d i n g   t h e   d e m o   C A . |
| `truststore_file_name` | str | `truststore.jks` | — |  |
| `truststore_password` | str | `password` | — |  |

Variables not listed here are undeclared in the argument spec; see `defaults/main.yml`.

<!-- END ROLE VARIABLES -->
