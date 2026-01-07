#!/bin/bash
set -e


############################
# Change to project directory: Để đảm bảo là nó đúng vị trí
############################
cd /home/javis-ai/Javis_AI_UAT/Javis_AI_DEMO/6804_DDQ


############################
# Instance / Port
############################
INSTANCE_ID=6868
PORT=6868
export PORT

############################
# Model & Cache directories
############################
export pHome="/home/javis-ai/Javis_AI_UAT/Javis_AI_DEMO/6804_DDQ"
export HF_HOME="${pHome}/data_models/models"
export TRANSFORMERS_CACHE="${pHome}/data_models/models"
export SENTENCE_TRANSFORMERS_HOME="${pHome}/data_models/models"
export PIXELTABLE_HOME="${pHome}/data_models/database/pixeltable"

############################
# TMPDIR
############################
export TMPDIR="/tmp/6804_DDQ/javis_${PORT}"

############################
# Create required directories
############################
mkdir -p "$TMPDIR"
mkdir -p "$HF_HOME"
mkdir -p "$TRANSFORMERS_CACHE"
mkdir -p "$SENTENCE_TRANSFORMERS_HOME"
mkdir -p "$PIXELTABLE_HOME"

chmod 700 "$TMPDIR"

############################
# Detect Python (venv first)
############################
PYTHON_PATH=""

if [ -f "/home/javis-ai/jai/bin/python" ]; then
    PYTHON_PATH="/home/javis-ai/jai/bin/python"
elif [ -f "../taEnv/bin/python" ]; then
    PYTHON_PATH="../taEnv/bin/python"
else
    PYTHON_PATH="python3"
fi

############################
# Run service
############################
echo "Using TMPDIR=$TMPDIR"
echo
echo "Starting Knowledge Base API on port $PORT..."
echo "Python: $PYTHON_PATH"
echo "Press Ctrl+C to stop"
echo

# Development mode – asyncio loop (Pixeltable compatible)
CUDA_VISIBLE_DEVICES=1 "$PYTHON_PATH" -m uvicorn ddq_main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --loop asyncio \
    --reload
