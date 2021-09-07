#!/usr/bin/env bash

ESC="\x1B"

# Pretty prompt
echo -e "$ESC[1;34mPyBraid Env Init$ESC[0m"

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

code .

# If command passed as argument, run it
if [ "$1" ]; then
    $@
fi
