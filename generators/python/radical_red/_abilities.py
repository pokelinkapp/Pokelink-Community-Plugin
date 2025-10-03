import pokelink.directories as directories
import pokelink.translations as translations

import json
import os

from pokelink import game_strings, translations
from pokelink.json_output import write_file

abilities = []

def generate():
    print("Generating Abilities")

    with open(os.path.join(directories.get_external_dir("rad-red-json"),
                           "abilities.json")) as data:
        ability_data = json.load(data)

        for key in ability_data:
            ability = ability_data[key]

            name = ability["names"][0]

            if not game_strings.has_ability(name):
                print(f"\tWARNING: Missing Pokelink translation for {name}")

                translations.add_translation(
                    f"RadicalRed.Ability.{game_strings.clean_up(name)}", name)

                name = f"RadicalRed.Ability.{game_strings.clean_up(name)}"
            else:
                name = "pokemon.ability." + game_strings.clean_up(name)

            abilities.insert(int(key), name)

    write_file(os.path.join(
        directories.get_output_dir("radred/v4.1/", True), "radred.abilities"),
               {"abilities": abilities})
