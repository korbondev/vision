#!/bin/bash

echo "Optimizating code for faster execution..."

# Requirements
export original_dir=$(pwd)

# Code optimization
find $original_dir/ -type f -name "*.py" -not -path "*/\.venv*/*" | while read -r file; do
    echo "Processing: $file"
    
    # Replace 'import base64' with 'import pybase64 as base64'
    sed -i 's/^import base64$/import pybase64 as base64/' "$file"
    
    # Replace 'import json' with 'import ujson as json'
    sed -i 's/^import json$/import ujson as json/' "$file"
done
echo "Done processing all .py files."