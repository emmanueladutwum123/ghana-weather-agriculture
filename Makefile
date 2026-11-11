# Rerun the whole project with `make all`.
PY := .venv/bin/python

.PHONY: all data figures paper venv clean-panel

all: data

venv:
	python3 -m venv .venv
	$(PY) -m pip install -r requirements.txt

data:
	$(PY) src/run_all.py

clean-panel:
	rm -f data/panel/*.csv
