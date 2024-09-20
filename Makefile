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

ANSIBLE_GALAXY_API_KEY ?= $(shell bash -c 'read -p "Enter your API key: " api_key; echo $$api_key')
.PHONY: publish
publish:
	@rm redpanda-cluster-*.tar.gz
	ansible-galaxy collection build && \
	ansible-galaxy collection publish redpanda-cluster-*.tar.gz --token $(ANSIBLE_GALAXY_API_KEY) -s https://galaxy.ansible.com/api/
