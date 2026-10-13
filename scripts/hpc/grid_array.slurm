#!/bin/bash
# Slurm array job: one task per (noise profile, depth). Each task evaluates every
# legal move of that level on one node. Merge with scripts/hpc/merge_grids.py.
#SBATCH --job-name=sentinels-grid
#SBATCH --array=0-5
#SBATCH --cpus-per-task=16
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=logs/%x-%A_%a.out
set -euo pipefail
PROFILES=(qff-synthetic qff-synthetic qff-synthetic fake-fez fake-fez fake-fez)
DEPTHS=(6 12 18 6 12 18)
P=${PROFILES[$SLURM_ARRAY_TASK_ID]}
D=${DEPTHS[$SLURM_ARRAY_TASK_ID]}
mkdir -p logs results/data/parts
export PYTHONPATH=src OMP_NUM_THREADS=1
python experiments/e0_game_grid.py --profile "$P" --depths "$D" \
  --workers "$SLURM_CPUS_PER_TASK" --out "results/data/parts/grid_${P}_d${D}.json"
