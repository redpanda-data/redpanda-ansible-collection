## System Setup for Redpanda Clusters

Handles system configuration on individual brokers for a Redpanda cluster. This entails:
* copying over certs
* handling the configuration of the data directory
* ensuring the data directory has correct permissions
* installing dependencies on the node required for Redpanda to run

If you handle this with a prebuilt node image and/or internal tooling you don't need to include this role in any plays. 

### Data directory mounting

The data volume is formatted as XFS and mounted by its **filesystem UUID** rather than by
the kernel device path. NVMe device names (e.g. `/dev/nvme0n1`) are assigned in discovery
order and are not guaranteed to be stable across reboots, so a UUID-based `/etc/fstab` entry
keeps the mount pointing at the correct volume.

| Variable | Default | Description |
| --- | --- | --- |
| `redpanda_mount_dir` | `/mnt/vectorized/redpanda` | Subdirectory on the mounted data volume that holds Redpanda's data. The historical (misspelled) `repdanda_mount_dir` is still honored if set, but emits a deprecation warning. |
| `redpanda_mount_point` | parent of `redpanda_mount_dir` (`/mnt/vectorized` by default) | Where the data volume is mounted. Derived from `redpanda_mount_dir`, so overriding the data dir moves the mount along with it; override this only when the volume must be mounted somewhere other than the data dir's parent. |
| `allow_unmounted_data_dir` | `false` | When no eligible (unpartitioned, `nvme*`-named) data device is found and the data dir is not already backed by a mounted filesystem, the role fails rather than silently placing Redpanda data on the root disk. Set to `true` to accept an unmounted data dir anyway (unsafe for production). |
| `data_dir_device_timeout` | `15s` | Caps how long systemd waits for the data device at boot (`x-systemd.device-timeout`) before continuing, preventing the default 90-second hang when a volume is slow to attach. |
| `ephemeral_disk` | `false` | When `true`, adds `nofail` to the mount options so a missing ephemeral disk does not block boot. Persistent volumes intentionally block boot if the device is absent. |
