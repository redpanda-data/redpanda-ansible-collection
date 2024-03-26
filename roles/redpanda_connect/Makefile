.PHONY: test reqs do

PYTHON ?= python
PIP ?= pip

DIR := tests
TESTS := $(wildcard $(DIR)/*_test.py)

# Target to process each file
all: $(FILES)

do: reqs test

test: $(TESTS)
	echo "running $(DIR) $(TESTS)"
	$(foreach script,$(SCRIPTS),echo "Running $(script)";python $(script);)


reqs:
	$(PIP) install --no-cache-dir -r tests/requirements.txt
