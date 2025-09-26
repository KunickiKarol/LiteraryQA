#!/bin/bash
# Usage: ./clean_books.sh

set -xe

PYTHONPATH=. uv run src/clean_gutenberg_html.py --normalize # can be taken out 