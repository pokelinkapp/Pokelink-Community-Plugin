import pokelink.directories as directories

import json
import os

types = {}

def process():
    print("Loading Types")

    with open(os.path.join(directories.get_external_dir("rad-red-json"),
                           "types.json")) as data:
        type_data = json.load(data)

    for key in type_data:
        types[key] = type_data[key]