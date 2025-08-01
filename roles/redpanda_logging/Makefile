PYTHON ?= python
PIP ?= pip

DIR := tests
SCRIPTS := $(wildcard $(DIR)/*_test.py)

.PHONY: do
do: reqs test

.PHONY: test
test: $(SCRIPTS)
	@echo "running $(DIR) $(SCRIPTS)"
	@EXIT_CODE=0; \
	for FILE in $(SCRIPTS); do \
		echo "Running $$FILE"; \
		$(PYTHON) $$FILE || EXIT_CODE=1; \
	done; \
	exit $$EXIT_CODE

.PHONY: reqs
reqs:
	$(PIP) install --no-cache-dir -r tests/requirements.txt

.PHONY: up
up:
	docker build -t redpanda-logging-test . && docker run redpanda-logging-test

.PHONY: compose-up
compose-up:
	docker compose up --build