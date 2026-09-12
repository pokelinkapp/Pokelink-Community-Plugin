import os
import collections

import pokelink.directories as directories
import pokelink.translations as translations
from pokelink import game_strings
from pokelink.json_output import write_file

_PREFIX = "PokemonUnknown.Item."
_items: list = []
_item_name_by_constant: dict = {}

_DISPLAY_OVERRIDES = {}


def process():
    print("Processing Items")
    global _items, _item_name_by_constant

    lookup = {
        ca.replace("_", ""): ca
        for ca in game_strings._game_strings.get("en", {}).get("clean_items", [])
    }

    unordered = {}
    with open(os.path.join(directories.get_external_dir("pokemon-unknown"),
                           "cfru", "include", "constants", "items.h"), "r") as f:
        for line in f:
            line = line.split("//")[0].strip()
            if not line.startswith("#define ITEM_"):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            name = parts[1].removeprefix("ITEM_")
            if name == "NONE":
                continue
            try:
                unordered[int(parts[2])] = name
            except ValueError:
                pass

    ordered = collections.OrderedDict(sorted(unordered.items()))
    _items = [None] * (max(ordered) + 1)

    for index, name in ordered.items():
        if name in _DISPLAY_OVERRIDES:
            display = _DISPLAY_OVERRIDES[name]
        else:
            display = None

        if display is not None and game_strings.has_item(display):
            item_name = "pokemon.item." + game_strings.clean_up(display)
        else:
            lookup_key = name.lower().replace("_", "")
            if lookup_key in lookup:
                item_name = "pokemon.item." + lookup[lookup_key]
            else:
                if display is None:
                    display = " ".join(p[0].upper() + p[1:].lower() for p in name.split("_"))
                    print(f"\tWARNING: No Pokelink translation for item {display}")
                key = _PREFIX + game_strings.clean_up(display)
                translations.add_translation(key, display)
                item_name = key

        _item_name_by_constant[name] = item_name
        _items[index] = item_name


def generate():
    print("Generating Items")
    write_file(
        os.path.join(directories.get_output_dir("pokemon-unknown/v1.6/", True), "unknown.items"),
        {"items": _items}
    )


def get_item_by_constant(constant: str) -> str:
    return _item_name_by_constant.get(constant, "")
