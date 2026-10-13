# Spacetime Sentinels: common tasks.  `make help` lists them.
PY ?= python
WORKERS ?= 2
export PYTHONPATH := src

.PHONY: help install test lint grid experiments figures web report slides reproduce play serve clean

help:            ## show this help
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install:         ## install the package and dev tools
	$(PY) -m pip install -r requirements.txt && $(PY) -m pip install -e ".[dev]"

test:            ## run the test suite
	$(PY) -m pytest

lint:            ## static checks
	ruff check src tests experiments

grid:            ## exhaustive sweep of every legal move (both noise profiles)
	$(PY) experiments/e0_game_grid.py --profile qff-synthetic --workers $(WORKERS)
	$(PY) experiments/e0_game_grid.py --profile fake-fez --workers $(WORKERS)

experiments:     ## research experiments E1-E7
	cd experiments && $(PY) e1_check_count.py && $(PY) e2_t_count.py && $(PY) e3_magic_capacity.py \
	  && $(PY) e5_noise_sweep.py && $(PY) e6_validation.py && $(PY) e7_t_noise.py

figures:         ## all figures + web summary
	cd experiments && $(PY) make_figures.py && $(PY) make_numbers.py && $(PY) make_readme.py

web:             ## export game data for GitHub Pages (docs/)
	$(PY) -m sentinels.cli export results/data/grid_qff-synthetic.json results/data/grid_fake-fez.json --out docs/data

report:          ## build report/main.pdf
	cd report && latexmk -pdf -interaction=nonstopmode main.tex

slides:          ## build presentation/slides.pdf
	cd presentation && latexmk -pdf -interaction=nonstopmode slides.tex

reproduce: grid experiments figures web report   ## everything, from scratch

play:            ## play one round live in the terminal
	$(PY) -m sentinels.cli play

serve:           ## serve the web game locally on http://localhost:8000
	cd docs && $(PY) -m http.server 8000

clean:
	rm -rf .pytest_cache **/__pycache__ report/*.aux report/*.log report/*.out report/*.fls report/*.fdb_latexmk report/*.bbl report/*.blg
