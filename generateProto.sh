#! /bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

mkdir -p $SCRIPT_DIR/generators/python/proto/0.7.1

echo "Generating common"

protoc --proto_path="$SCRIPT_DIR/external/pokelink-protobufs/" --python_out="$SCRIPT_DIR/generators/python/proto" $SCRIPT_DIR/external/pokelink-protobufs/*.proto

echo "Generating 0.7.1"

protoc --proto_path="$SCRIPT_DIR/external/pokelink-protobufs/0.7.1/" --python_out="$SCRIPT_DIR/generators/python/proto/0.7.1" $SCRIPT_DIR/external/pokelink-protobufs/0.7.1/*.proto
