#!/bin/bash

# FBA Profit Analyzer - Quick Launch Script
# Automatically loads .env.fba and runs the analyzer

echo "======================================================================"
echo "FBA PROFIT ANALYZER"
echo "======================================================================"
echo ""

# Check if .env.fba exists
if [ ! -f ".env.fba" ]; then
    echo "⚠️  Configuration file .env.fba not found!"
    echo ""
    echo "Setup required:"
    echo "1. cp .env.fba.example .env.fba"
    echo "2. Edit .env.fba with your API credentials"
    echo "3. Run this script again"
    echo ""
    exit 1
fi

# Check if input file exists
INPUT_FILE=$(grep INPUT_CSV .env.fba | cut -d '=' -f2)
if [ -z "$INPUT_FILE" ]; then
    INPUT_FILE="master_product_catalog.csv"
fi

if [ ! -f "$INPUT_FILE" ]; then
    echo "⚠️  Input file not found: $INPUT_FILE"
    echo ""
    echo "Please ensure your product catalog CSV is in the current directory."
    echo ""
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env.fba | xargs)

echo "Configuration loaded from .env.fba"
echo "Input file: $INPUT_FILE"
echo ""
echo "Starting analysis..."
echo ""

# Run the analyzer
python3 fba_profit_analyzer.py

echo ""
echo "======================================================================"
echo "Done! Check the output file for results."
echo "======================================================================"
