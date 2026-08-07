# binary_bundler

Builds Redpanda package tarballs for airgapped installs: downloads the
packages for one exact version and architecture (stable or unstable
channel, optional checksums) into an isolated working directory and
archives them as `redpanda_debs.tar.gz` / `redpanda_rpms.tar.gz` in
`download_directory`.

Use as `redpanda.cluster.binary_bundler`, typically against localhost.
The tarball layout is what `redpanda_broker`'s airgap install tasks
expect (`<package>__standard.rpm` / `__noarch` / `__source` naming for
RPMs, plain package filenames for DEBs).

Note: Artifact Registry serves some direct-download paths with
content-hash filename suffixes; if a pinned URL 404s, verify the exact
object name in the repository pool.

## Variables

The load-bearing inputs are validated by `meta/argument_specs.yml` and
documented below; any further tunables live in `defaults/main.yml`.

<!-- BEGIN ROLE VARIABLES (generated from meta/argument_specs.yml; run scripts/generate-role-docs.py) -->

| Variable | Type | Default | Choices | Description |
|---|---|---|---|---|
| `redpanda_version` | str | *required* | — | E x a c t   v e r s i o n   t o   b u n d l e ;   l a t e s t   i s   n o t   s u p p o r t e d   h e r e . |
| `basearch` | str | *required* | — | T a r g e t   a r c h i t e c t u r e   a s   r e p o r t e d   b y   u n a m e   - m . |
| `rpm_or_deb` | str | *required* | `rpm`, `deb` |  |
| `is_using_unstable` | bool | `False` | — |  |
| `download_directory` | str | `/tmp` | — |  |
| `deb_checksums` | dict | `{}` | — |  |
| `rpm_checksums` | dict | `{}` | — |  |

Variables not listed here are undeclared in the argument spec; see `defaults/main.yml`.

<!-- END ROLE VARIABLES -->
