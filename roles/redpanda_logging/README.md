# Redpanda Logging Role

This Ansible role configures centralized logging for Redpanda to a dedicated log file, preventing system log pollution and providing better log management capabilities.

## Overview

The role addresses the issue of Redpanda logs mixing with system logs by:
- Redirecting logs to `/var/log/redpanda.log`
- Setting up log rotation to prevent disk space issues
- Configuring proper permissions and ownership
- Supporting both rsyslog and systemd logging configurations

## Requirements

- Ansible 2.9 or higher
- Target systems running systemd
- Package manager (apt, yum, dnf, etc.) available for installing logging backends
- logrotate installed on target systems (for log rotation)

Note: The role will automatically install rsyslog or syslog-ng as needed based on the selected backend.

## Role Variables

### Basic Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `redpanda_logging_enabled` | `true` | Enable/disable logging configuration |
| `redpanda_logging_log_file` | `/var/log/redpanda.log` | Redpanda log file path |

### Permissions

| Variable | Default | Description |
|----------|---------|-------------|
| `redpanda_logging_owner` | `syslog` | Log file owner |
| `redpanda_logging_group` | `adm` | Log file group |
| `redpanda_logging_dir_mode` | `0755` | Log directory permissions |
| `redpanda_logging_file_mode` | `0640` | Log file permissions |

### Rsyslog Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `redpanda_logging_rsyslog_enabled` | `true` | Enable rsyslog configuration |
| `redpanda_logging_rsyslog_priority` | `40` | Rsyslog config file priority |
| `redpanda_logging_program` | `rpk` | Syslog program name for Redpanda |

### Logrotate Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `redpanda_logging_logrotate_enabled` | `true` | Enable logrotate configuration |
| `redpanda_logging_logrotate_frequency` | `daily` | Log rotation frequency |
| `redpanda_logging_logrotate_rotate` | `7` | Number of rotated logs to keep |
| `redpanda_logging_logrotate_maxsize` | `100M` | Maximum log file size before rotation |
| `redpanda_logging_logrotate_compress` | `true` | Compress rotated logs |
| `redpanda_logging_logrotate_delaycompress` | `true` | Delay compression until next rotation |
| `redpanda_logging_logrotate_notifempty` | `true` | Don't rotate empty logs |

### Systemd Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `redpanda_logging_systemd_enabled` | `false` | Enable systemd-specific logging config |
| `redpanda_logging_systemd_max_level` | `info` | Maximum log level for journald |
| `redpanda_logging_systemd_forward_to_syslog` | `true` | Forward systemd logs to syslog |

## Dependencies

None. This role is designed to work independently.

## Example Playbook

### Basic Usage

```yaml
- hosts: redpanda_nodes
  roles:
    - role: redpanda_logging
```

### Custom Configuration

```yaml
- hosts: redpanda_nodes
  roles:
    - role: redpanda_logging
      vars:
        redpanda_logging_log_file: /data/logs/redpanda.log
        redpanda_logging_logrotate_rotate: 14
        redpanda_logging_logrotate_maxsize: 500M
```

### Enterprise Configuration with Custom Mount Point

```yaml
- hosts: redpanda_nodes
  roles:
    - role: redpanda_logging
      vars:
        # Use custom log file path
        redpanda_logging_log_file: /app/logs/redpanda.log
        
        # Keep more logs for compliance
        redpanda_logging_logrotate_rotate: 30
        redpanda_logging_logrotate_maxsize: 1G
        
        # Custom ownership if needed
        redpanda_logging_owner: redpanda
        redpanda_logging_group: redpanda
```

## How It Works

1. **Directory Creation**: Creates the log directory structure with proper permissions
2. **Rsyslog Configuration**: Deploys rsyslog rules to filter Redpanda logs by program name
3. **Log File Creation**: Creates initial log files with correct ownership
4. **Logrotate Setup**: Configures automatic log rotation to prevent disk space issues
5. **Service Integration**: Optionally configures systemd service overrides for consistent logging

## Troubleshooting

### Logs Not Appearing

1. Check rsyslog is running: `systemctl status rsyslog`
2. Verify rsyslog configuration: `rsyslogd -N1`
3. Check service is using correct syslog identifier: `journalctl -u redpanda -o json | grep SYSLOG_IDENTIFIER`

### Permission Issues

1. Verify log file ownership: `ls -la /var/log/redpanda.log`
2. Check SELinux context if enabled: `ls -Z /var/log/redpanda.log`
3. Ensure rsyslog can write to log file: `sudo -u syslog touch /var/log/redpanda.log`

### Log Rotation Not Working

1. Test logrotate configuration: `logrotate -d /etc/logrotate.d/redpanda`
2. Force rotation: `logrotate -f /etc/logrotate.d/redpanda`
3. Check logrotate status: `cat /var/lib/logrotate/status`

## License

Same as redpanda-ansible-collection

## Author Information

Created for the redpanda-ansible-collection to address enterprise logging requirements.