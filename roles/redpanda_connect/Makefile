.PHONY: test reqs do

PYTHON ?= python
PIP ?= pip

DIR := tests
SCRIPTS := $(wildcard $(DIR)/*.py)

# Target to process each file
all: $(FILES)

do: reqs test

test: $(SCRIPTS)
	echo "running $(DIR) $(SCRIPTS)"
	$(foreach script,$(SCRIPTS),echo "Running $(script)";python $(script);)


reqs:
	$(PIP) install --no-cache-dir -r tests/requirements.txt
