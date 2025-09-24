#!/bin/bash
# Script to download books from the NarrativeQA dataset
# Usage: ./download_books.sh <dash-separated list of splits>
# Example: ./download_books.sh test-train

set -xe

splits=${1:-"test-train-validation"}

PYTHONPATH=. uv run ./src/download_narrativeqa_html.py \
    --nqa_hf_path deepmind/narrativeqa \
    --output_dir data/narrativeqa \
    --splits $splits