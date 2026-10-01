import os
import collections

import pokelink.directories as directories
import pokelink.translations as translations
from pokelink import game_strings
from pokelink.json_output import write_file
from pokemon_unknown._util import strip_comments

_PREFIX = "PokemonUnknown.Ability."
_abilities: list = []
_ability_name_by_constant: dict = {}

_DISPLAY_OVERRIDES = {
    "GULPMISSLE": "Gulp Missile",
    "LETTERSWARM": "Letter Swarm",
}


def process():
    print("Processing Abilities")
    global _abilities

    # Create a lookup from game strings without underscores
    lookup = {
        ca.replace("_", ""): ca
        for ca in game_strings._game_strings.get("en", {}).get("clean_abilities", [])
    }

    unordered = {}
    with open(os.path.join(directories.get_external_dir("pokemon-unknown"),
                           "cfru", "include", "constants", "abilities.h"), "r") as f:
        for line in strip_comments(f.read()).splitlines():
            line = line.strip()
            if not line.startswith("#define ABILITY_"):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            name = parts[1].removeprefix("ABILITY_")
            if name == "NONE":
                continue
            unordered[int(parts[2], 16)] = name

    ordered = collections.OrderedDict(sorted(unordered.items()))
    _abilities = [None] * max(ordered)

    for index, name in ordered.items():
        slot = index - 1
        if name in _DISPLAY_OVERRIDES:
            display = _DISPLAY_OVERRIDES[name]
        else:
            display = None

        if display is not None and game_strings.has_ability(display):
            _abilities[slot] = "pokemon.ability." + game_strings.clean_up(display)
            continue

        lookup_key = name.lower().replace("_", "")
        if lookup_key in lookup:
            _abilities[slot] = "pokemon.ability." + lookup[lookup_key]
        else:
            if display is None:
                display = " ".join(p[0].upper() + p[1:].lower() for p in name.split("_"))
                print(f"\tWARNING: No Pokelink translation for {display}")
            key = _PREFIX + game_strings.clean_up(display)
            translations.add_translation(key, display)
            _abilities[slot] = key

        _ability_name_by_constant[name] = _abilities[slot]


def generate():
    print("Generating Abilities")
    write_file(
        os.path.join(directories.get_output_dir("pokemon-unknown/v1.6/", True), "unknown.abilities"),
        {"abilities": _abilities}
    )


def get_ability(index: int) -> str:
    if 0 <= index < len(_abilities):
        return _abilities[index] or ""
    return ""


def get_ability_by_constant(constant: str) -> str:
    return _ability_name_by_constant.get(constant, "")
