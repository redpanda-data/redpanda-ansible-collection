# sysctl_setup

Applies and persists the kernel settings Redpanda needs:
`fs.inotify.max_user_instances` (Schema Registry misbehaves when the
default is too low) and `kernel.panic_on_oops` (Redpanda recommends
panicking immediately on kernel oops).

Use as `redpanda.cluster.sysctl_setup`.

## Variables

The load-bearing inputs are validated by `meta/argument_specs.yml` and
documented below; any further tunables live in `defaults/main.yml`.

<!-- BEGIN ROLE VARIABLES (generated from meta/argument_specs.yml; run scripts/generate-role-docs.py) -->

| Variable | Type | Default | Choices | Description |
|---|---|---|---|---|
| `max_user_instances` | int | `8192` | — | f s . i n o t i f y . m a x _ u s e r _ i n s t a n c e s   v a l u e . |
| `kernel_panic_on_oops` | int | `1` | `0`, `1` | W h e t h e r   t h e   k e r n e l   p a n i c s   i m m e d i a t e l y   o n   a n   o o p s . |

Variables not listed here are undeclared in the argument spec; see `defaults/main.yml`.

<!-- END ROLE VARIABLES -->
