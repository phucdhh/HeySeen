#!/bin/bash
cd /Users/m2pro/HeySeen
source .venv/bin/activate
for pdf in internet_data_test/pdf/*.pdf; do
    filename=$(basename "$pdf" .pdf)
    if [ -f "internet_data_test/tex_result/$filename.tex" ]; then
        echo "Skipping $filename (already done)"
        continue
    fi
    echo "Processing $filename"
    python heyseen/cli/main.py convert "$pdf" -o "internet_data_test/tex_result/$filename" --quiet
    if [ -f "internet_data_test/tex_result/$filename/main.tex" ]; then
        mv "internet_data_test/tex_result/$filename/main.tex" "internet_data_test/tex_result/$filename.tex"
        rm -rf "internet_data_test/tex_result/$filename"
    fi
done