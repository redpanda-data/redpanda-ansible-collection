PYTHON ?= python
PIP ?= pip

DIR := tests
SCRIPTS := $(wildcard $(DIR)/*_test.py)

# Target to process each file
.PHONY: all
all: $(FILES)

.PHONY: do
do: mocks test

.PHONY: mocks
mocks:
	mkdir -p /app/library && \
	cp tests/mocks/* /app/library

.PHONY: test
test: $(SCRIPTS)
	echo "running $(DIR) $(SCRIPTS)"
	$(foreach FILE,$(SCRIPTS), $(PYTHON) $(FILE);)

.PHONY: up
up:
	docker-compose up --build
