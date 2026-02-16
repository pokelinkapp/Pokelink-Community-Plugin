import pokelink.directories as directories

import json
import os

from pokelink import game_strings, translations
from pokelink.json_output import write_file

items = []
_item_id = {}

def generate():
    print("Generating Items")

    with open(os.path.join(directories.get_external_dir("rad-red-json"),
                           "items.json")) as data:
        item_data = json.load(data)

        for key in item_data:
            item = item_data[key]

            if item is None:
                items.insert(int(key), None)
                continue

            name = item["name"]

            if not game_strings.has_item(name):
                print(f"\tWARNING: Missing Pokelink translation for {name}")

                translations.add_translation(
                    f"RadicalRed.Item.{game_strings.clean_up(name)}", name)

                name = f"RadicalRed.Item.{game_strings.clean_up(name)}"
            else:
                name = "pokemon.item." + game_strings.clean_up(name)

            items.insert(int(key), name)

    write_file(os.path.join(
        directories.get_output_dir("radred/v4.1/", True), "radred.items"),
               {"items": [None] + items})
