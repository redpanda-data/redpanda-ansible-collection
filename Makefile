# run ansible lint using the config file
.PHONY: lint
lint:
	@echo "Running ansible-lint"
	@ansible-lint -c .ansible-lint

# lint the binary_bundler role in roles/binary_bundler
.PHONY: lint-binary_bundler
lint-binary_bundler:
	@echo "Running ansible-lint on binary_bundler role"
	@ansible-lint -c .ansible-lint roles/binary_bundler

# lint the client config role in roles/client_config
.PHONY: lint-client_config
lint-client_config:
	@echo "Running ansible-lint on client_config role"
	@ansible-lint -c .ansible-lint roles/client_config

# lint the demo_certs role in roles/demo_certs
.PHONY: lint-demo_certs
lint-demo_certs:
	@echo "Running ansible-lint on demo_certs role"
	@ansible-lint -c .ansible-lint roles/demo_certs

# lint the redpanda_broker role in roles/redpanda_broker
.PHONY: lint-redpanda_broker
lint-redpanda_broker:
	@echo "Running ansible-lint on redpanda_broker role"
	@ansible-lint -c .ansible-lint roles/redpanda_broker

# lint the redpanda_connect role in roles/redpanda_connect
.PHONY: lint-redpanda_connect
lint-redpanda_connect:
	@echo "Running ansible-lint on redpanda_connect role"
	@ansible-lint -c .ansible-lint roles/redpanda_connect

# lint the redpanda_console role in roles/redpanda_console
.PHONY: lint-redpanda_console
lint-redpanda_console:
	@echo "Running ansible-lint on redpanda_console role"
	@ansible-lint -c .ansible-lint roles/redpanda_console

# lint the systemctl_setup role in roles/systemctl_setup
.PHONY: lint-systemctl_setup
lint-sysctl_setup:
	@echo "Running ansible-lint on systemctl_setup role"
	@ansible-lint -c .ansible-lint roles/sysctl_setup

# lint the system_setup role in roles/system_setup
.PHONY: lint-system_setup
lint-system_setup:
	@echo "Running ansible-lint on system_setup role"
	@ansible-lint -c .ansible-lint roles/system_setup

SHELL := bash
DIST_DIR ?= dist
VERSION := $(shell sed -n 's/^version: *//p' galaxy.yml)
ARTIFACT = $(DIST_DIR)/redpanda-cluster-$(VERSION).tar.gz

# Build the collection from a git archive of HEAD, so only committed files can
# ship: ansible-galaxy packages whatever directory it is given and ignores
# .gitignore, which is how local state (assistant settings, virtualenvs, IDE
# files, logs) once reached Galaxy.
.PHONY: build
build:
	@set -euo pipefail; \
	if ! git diff --quiet HEAD --; then \
		echo "tracked files differ from HEAD; commit or stash before building" >&2; exit 1; \
	fi; \
	stage=$$(mktemp -d); trap 'rm -rf "$$stage"' EXIT; \
	git archive --format=tar HEAD | tar -x -C "$$stage"; \
	mkdir -p "$(DIST_DIR)"; \
	ansible-galaxy collection build --force --output-path "$(abspath $(DIST_DIR))" "$$stage"

# Refuse to publish an artifact that carries any dot-path.
.PHONY: verify-artifact
verify-artifact: build
	@set -euo pipefail; \
	if tar -tzf "$(ARTIFACT)" | grep -E '(^|/)\.'; then \
		echo "refusing to publish: dot-paths found in $(ARTIFACT)" >&2; exit 1; \
	fi; \
	echo "$(ARTIFACT): $$(tar -tzf "$(ARTIFACT)" | wc -l | tr -d ' ') entries, no dot-paths"

.PHONY: test-packaging
test-packaging:
	python3 -m pytest tests/packaging -v -p no:cacheprovider

ANSIBLE_GALAXY_API_KEY ?= $(shell bash -c 'read -s -p "Enter your API key: " api_key; echo $$api_key')
.PHONY: publish
publish: verify-artifact
	ansible-galaxy collection publish "$(ARTIFACT)" --token $(ANSIBLE_GALAXY_API_KEY) -s https://galaxy.ansible.com/api/
