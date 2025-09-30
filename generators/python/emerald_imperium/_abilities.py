import pokelink.directories as directories
import pokelink.translations as translations

from pokelink import strip_comments, game_strings
from pokelink.json_output import write_file

import os
import collections

_abilities = []

_ability_prefix = "EmeraldImperium.Ability."

def process():
    print("Processing Abilities")
    unordered = {}
    global _abilities

    with open(os.path.join(directories.get_external_dir("emerald-imperium"),
                           "include", "constants", "abilities.h"), "r") as file:
        ability_lines = [strip_comments(line) for line in file]

        for line in ability_lines:
            if not line:
                continue

            if not line.startswith("#define ABILITY_"):
                continue

            items = line.replace("ABILITY_", "").split(" ")

            if items[1] == "NONE":
                continue

            unordered[int(items[2])] = items[1]

        ordered_index = collections.OrderedDict(sorted(unordered.items()))

        for index in ordered_index:
            ability = ordered_index[index]

            split = ability.split("_")

            first = True

            for item in split:
                if first:
                    first = False
                    ability = item[0] + item[1:].lower()
                    continue

                ability += " " + item[0] + item[1:].lower()

            translations.add_translation(_ability_prefix + game_strings.clean_up(ability), ability)

            _abilities.append(_ability_prefix + game_strings.clean_up(ability))


def generate():
    print("Generating Abilities")

    write_file(
        os.path.join(directories.get_output_dir("emerald_imperium", True),
                     "emeraldImperium.abilities"), {"abilities": _abilities})


def get_ability(index: int) -> str:
    return _abilities[index]