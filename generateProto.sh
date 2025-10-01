#! /bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

mkdir -p $SCRIPT_DIR/generators/python/pokelink/proto/v0_7_1

echo "Generating common"

cd ./generators/python

source ./.venv/bin/activate

cd ../..

protoc --proto_path="$SCRIPT_DIR/external/pokelink-protobufs/" --python_out="$SCRIPT_DIR/generators/python/pokelink/proto" --mypy_out="$SCRIPT_DIR/generators/python/pokelink/proto" $SCRIPT_DIR/external/pokelink-protobufs/*.proto

echo "Generating 0.7.1"

protoc --proto_path="$SCRIPT_DIR/external/pokelink-protobufs/0.7.1/" --python_out="$SCRIPT_DIR/generators/python/pokelink/proto/v0_7_1" --mypy_out="$SCRIPT_DIR/generators/python/pokelink/proto/v0_7_1" $SCRIPT_DIR/external/pokelink-protobufs/0.7.1/*.proto
