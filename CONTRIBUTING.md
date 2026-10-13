# Contributing

Thanks for your interest. Spacetime Sentinels has one hard rule: **every number shown to a player must come from a Qiskit computation.** New mechanics are welcome as long as they keep that rule and map cleanly onto the physics.

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
make install
make test
```

## Workflow

1. Open an issue describing the change and the physics it represents.
2. Create a branch, keep commits focused, run `make lint test`.
3. If results change, rerun `make grid figures web` and commit the updated `results/` and `docs/data/`.
4. Open a pull request using the template.

## Code style

Ruff for linting (`ruff check`), type hints on public functions, docstrings that state the physics, and tests for every new invariant (for example, "a check never fires on the ideal circuit").
