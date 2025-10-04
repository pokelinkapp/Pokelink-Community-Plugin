import pokelink.directories as directories
import pokelink.translations as translations

import json
import os

from pokelink import game_strings, translations
from radical_red._types import types
from pokelink.json_output import write_file

moves = []

def generate():
    print("Generating Abilities")

    with open(os.path.join(directories.get_external_dir("rad-red-json"),
                           "moves.json")) as data:
        move_data = json.load(data)

        for key in move_data:
            move = move_data[key]

            out_move = dict()
            out_move["id"] = move["ID"]
            name = move["name"]

            if not game_strings.has_move(name):
                print(f"\tWARNING: Missing Pokelink translation for {name}")

                translations.add_translation(
                    f"RadicalRed.Move.{game_strings.clean_up(name)}", name)

                name = f"RadicalRed.Move.{game_strings.clean_up(name)}"
            else:
                name = f"pokemon.move.{game_strings.clean_up(name)}"

            out_move["name"] = name

            out_move["power"] = move["power"]
            out_move["type"] = f"pokemon.type.{game_strings.clean_up(types[str(move["type"])])}"
            out_move["accuracy"] = move["accuracy"]
            out_move["pp"] = move["pp"]
            out_move["priority"] = move["priority"]
            out_move["category"] = f"pokemon.category.move.{"physical" if move["split"] == 0 else "special" if move["split"] == 1 else "status"}"

            moves.insert(int(key), out_move)

    write_file(os.path.join(
        directories.get_output_dir("radred/v4.1/", True), "radred.moves"),
               moves)