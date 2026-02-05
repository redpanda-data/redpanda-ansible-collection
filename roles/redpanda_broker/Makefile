PYTHON ?= python
PIP ?= pip

DIR := tests
SCRIPTS := $(wildcard $(DIR)/*_test.py)

# Target to process each file
.PHONY: all
all: $(FILES)

.PHONY: shellcheck
shellcheck:
	shellcheck files/idempotent-config-set.sh

.PHONY: bats
bats:
	bats tests/*.bats

.PHONY: do
do: mocks shellcheck bats test

.PHONY: mocks
mocks:
	mkdir -p /app/library && \
	cp tests/mocks/* /app/library

.PHONY: test
test: $(SCRIPTS)
	@echo "running $(DIR) $(SCRIPTS)"
	@EXIT_CODE=0; \
	for FILE in $(SCRIPTS); do \
		echo "Running $$FILE"; \
		$(PYTHON) $$FILE || EXIT_CODE=1; \
	done; \
	exit $$EXIT_CODE

.PHONY: up
up:
	docker build -t redpanda-broker-test . && docker run redpanda-broker-test

.PHONY: compose-up
compose-up:
	docker compose up --build
