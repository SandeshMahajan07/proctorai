#!/usr/bin/env bash
set -e

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Downloading face landmark model..."
MODEL_PATH="ai_modules/lbfmodel.yaml"
if [ ! -f "$MODEL_PATH" ]; then
    curl -L "https://github.com/kurnianggoro/GSOC2017/raw/master/data/lbfmodel.yaml" \
         -o "$MODEL_PATH"
    echo "==> lbfmodel.yaml downloaded."
else
    echo "==> lbfmodel.yaml already present, skipping."
fi

echo "==> Build complete."