.PHONY: test reqs do

PYTHON ?= python
PIP ?= pip

DIR := tests
SCRIPTS := $(wildcard $(DIR)/*_test.py)

# Target to process each file
all: $(FILES)

do: reqs test

test: $(SCRIPTS)
	echo "running $(DIR) $(SCRIPTS)"
	$(foreach FILE,$(SCRIPTS), $(PYTHON) $(FILE);)

reqs:
	$(PIP) install --no-cache-dir -r tests/requirements.txt

up:
	docker-compose up --build
