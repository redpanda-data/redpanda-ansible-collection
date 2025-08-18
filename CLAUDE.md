# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Redpanda Ansible Collection (`redpanda.cluster`) that enables provisioning and managing Redpanda clusters. It provides roles for deploying Redpanda brokers, Connect, Console, logging, system setup, and certificate management.

## Commands

### Linting
- `make lint` - Run ansible-lint on all roles using `.ansible-lint` config
- `make lint-<role_name>` - Lint specific roles (e.g., `make lint-redpanda_broker`)

### Testing
- Python tests are located in `roles/*/tests/` directories
- Run tests with `pytest` in individual role test directories
- Test requirements are in `roles/*/tests/requirements.txt` files

### Building and Publishing
- `ansible-galaxy collection build` - Build the collection
- `make publish` - Build and publish to Ansible Galaxy (requires API key)

## Architecture

### Collection Structure
The collection follows standard Ansible collection layout with these key roles:

**Core Roles:**
- `redpanda_broker/` - Main role for installing and configuring Redpanda brokers
- `redpanda_connect/` - Deploys Redpanda Connect (Kafka Connect alternative)  
- `redpanda_console/` - Deploys Redpanda Console (web UI)
- `redpanda_logging/` - Configures logging with rsyslog and logrotate
- `system_setup/` - System dependencies and user/directory setup
- `sysctl_setup/` - System tuning and kernel parameters

**Support Roles:**
- `demo_certs/` - Generates demo TLS certificates (testing only)
- `client_config/` - Configures client tools like `rpk`
- `binary_bundler/` - Creates offline installation bundles

### Key Configuration Patterns

**Package Installation:**
- Supports both RPM (RedHat family) and DEB (Debian family) systems
- Has separate tasks for online repo-based and airgap installations
- Handles both stable and nightly development builds

**TLS Support:**
- Certificate management through `demo_certs/` role or external certificates
- Templates handle TLS configuration in `redpanda.yml` and other config files

**Multi-OS Support:**
- Uses `ansible_os_family` and `ansible_distribution` for OS-specific logic
- Separate task files for DEB/RPM package management

### Template System
Configuration templates are in `roles/*/templates/`:
- `redpanda_broker/templates/redpanda.yml` - Main Redpanda configuration
- `redpanda_connect/templates/connect-distributed/` - Connect worker configuration  
- `redpanda_console/templates/console.yml` - Console configuration

### Default Variables
Each role has extensive defaults in `roles/*/defaults/main.yml` covering:
- Port configurations (Kafka 9092, Admin API 9644, RPC 33145)
- Repository URLs and package versions
- TLS certificate paths
- Performance and operational settings

## Development Workflow

1. Make changes to roles in `roles/` directory
2. Run `make lint` to check Ansible best practices
3. Test changes using role-specific tests in `roles/*/tests/`
4. Update version in `galaxy.yml` before publishing
5. Use `make publish` to release to Ansible Galaxy

## Testing Notes

- Each role has Python-based unit tests using pytest
- Tests validate Jinja2 template rendering and configuration generation
- Docker Compose files in role directories support local testing
- Mock Ansible modules in `roles/redpanda_broker/library/` for testing