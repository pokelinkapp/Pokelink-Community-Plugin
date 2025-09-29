#! /bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd "$SCRIPT_DIR"

git submodule update --init --recursive

cd ./generators/python

python -m venv ./.venv

source ./.venv/bin/activate

pip install -r ./requirements.txt

cd "$SCRIPT_DIR"

./generateProto.sh
