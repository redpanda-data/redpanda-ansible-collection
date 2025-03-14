.PHONY: test reqs do

PYTHON ?= python
PIP ?= pip

DIR := tests
SCRIPTS := $(wildcard $(DIR)/*_test.py)

# Target to process each file
all: $(FILES)

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
reqs:
	$(PIP) install --no-cache-dir -r tests/requirements.txt

up:
	docker-compose up --build
