import proto.v0_7_1.pokedex_pb2 as pb_pokedex
import pokelink.directories as directories
from google.protobuf import json_format
from pokelink.json_output import write_file

import os


dex = pb_pokedex.Pokedex()

dex.version = "0.7.1"
dex.entries.append(pb_pokedex.Species())

def process():
    print("Processing Pokedex")


def generate():
    print("Generating Pokedex")

    write_file(os.path.join(directories.get_output_dir("emerald_imperium", True), "dex.py.json"), json_format.MessageToDict(dex))