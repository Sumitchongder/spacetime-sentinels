#!/usr/bin/env bash
# Reproduce every result, figure, the web data and the report on one machine.
# About 1 to 2 hours on a 2-core laptop; minutes on a cluster (see scripts/hpc).
set -euo pipefail
cd "$(dirname "$0")/.."
make grid WORKERS="${WORKERS:-$(nproc)}"
make experiments
make figures
make web
make report
echo "Done. Open docs/index.html via 'make serve'."
