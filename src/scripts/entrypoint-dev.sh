#!/bin/bash

cd /home/runner/src

# Check if "venv" exists in the current directory.
if [ -d "venv" ]; then
    echo "Found venv in the current directory. Removing it..."
    rm -rf "venv"
fi

# Check if "venv" exists in the /var/tmp/deps directory.
if [ -d "/var/tmp/deps/venv" ]; then
    echo "Found venv in /var/tmp/deps. Moving it to the current directory..."
    mv "/var/tmp/deps/venv" .
else
    echo "Error: venv folder not found in /var/tmp/deps." >&2
    exit 1
fi

exec /bin/bash --rcfile <(echo "source ~/.bashrc; source venv/bin/activate")

