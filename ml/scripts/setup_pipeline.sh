#!/bin/bash

# Solar Cycle ML Pipeline Setup Script
# Downloads data, preprocesses, and engineers features

set -e  # Exit on error

echo "========================================="
echo "Solar Cycle ML Pipeline Setup"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python installation
echo -e "${YELLOW}Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.10+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

# Check if in correct directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: Not in ml/ directory. Please run from ml/ directory.${NC}"
    exit 1
fi

# Create virtual environment
echo ""
echo -e "${YELLOW}Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo ""
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create directories
echo ""
echo -e "${YELLOW}Creating directory structure...${NC}"
mkdir -p data/{raw,processed,features}
mkdir -p models/{short_term_lstm,long_term_lstm_fcn,anomaly_autoencoder,ensemble}
mkdir -p logs/ml
mkdir -p mlruns
mkdir -p notebooks
echo -e "${GREEN}✓ Directories created${NC}"

# Download data
echo ""
echo -e "${YELLOW}Step 1/3: Downloading solar data...${NC}"
python3 src/data/download_data.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Data download completed${NC}"
else
    echo -e "${RED}✗ Data download failed${NC}"
    exit 1
fi

# Preprocess data
echo ""
echo -e "${YELLOW}Step 2/3: Preprocessing data...${NC}"
python3 src/data/preprocess.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Data preprocessing completed${NC}"
else
    echo -e "${RED}✗ Data preprocessing failed${NC}"
    exit 1
fi

# Feature engineering
echo ""
echo -e "${YELLOW}Step 3/3: Engineering features...${NC}"
python3 src/data/feature_engineering.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Feature engineering completed${NC}"
else
    echo -e "${RED}✗ Feature engineering failed${NC}"
    exit 1
fi

# Summary
echo ""
echo "========================================="
echo -e "${GREEN}Pipeline Setup Complete!${NC}"
echo "========================================="
echo ""
echo "Data files created:"
echo "  - data/raw/sidc_sunspot_daily.csv"
echo "  - data/processed/daily_processed.csv"
echo "  - data/features/daily_features.csv"
echo ""
echo "Next steps:"
echo "  1. Train models:"
echo "     python3 src/training/train_short_term.py"
echo ""
echo "  2. Start API server:"
echo "     uvicorn src.serving.api:app --reload"
echo ""
echo "  3. Start MLflow UI:"
echo "     mlflow ui"
echo ""
echo "  4. Explore in Jupyter:"
echo "     jupyter notebook notebooks/"
echo ""

# Check data files
echo "Data summary:"
if [ -f "data/features/daily_features.csv" ]; then
    NUM_ROWS=$(wc -l < data/features/daily_features.csv)
    NUM_COLS=$(head -1 data/features/daily_features.csv | tr ',' '\n' | wc -l)
    echo "  - Samples: $NUM_ROWS"
    echo "  - Features: $NUM_COLS"
fi

echo ""
echo -e "${GREEN}Ready to train models!${NC}"
