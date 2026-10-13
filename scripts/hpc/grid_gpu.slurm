#!/bin/bash
# Larger studies (more qubits or checks) on GPU nodes with qiskit-aer-gpu.
#SBATCH --job-name=sentinels-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --output=logs/%x-%j.out
set -euo pipefail
export PYTHONPATH=src
python experiments/e0_game_grid.py --profile qff-synthetic --n 8 --budget 6 \
  --device GPU --workers 1 --out results/data/grid_gpu_n8.json
