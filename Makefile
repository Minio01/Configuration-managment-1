PYTHON = python

.PHONY: run test

run:
	$(PYTHON) src/main.py

test:
	$(PYTHON) -m unittest discover -s tests -v
