import pokelink.directories as directories
import pokelink.translations as translations

from pokelink import strip_comments, game_strings
from pokelink.json_output import write_file

import os
import collections

_items: list[str] = []

_items_prefix = "EmeraldImperium.Item."

def process():
    print("Processing Items")

    item_strings = dict()

    with open(os.path.join(directories.get_external_dir("emerald-imperium"),
                           "include", "constants", "items.h"), "r") as file:
        item_lines = [strip_comments(line) for line in file]

        max_value = 0

        for line in item_lines:
            if not line:
                continue

            if line.startswith("#define ITEMS_COUNT"):
                break

            if not line.startswith("#define ITEM_") or line.startswith("#define ITEM_NONE") or line.endswith("0xFFFF"):
                continue


            items = line.replace("ITEM_", "", 1).split(" ")

            if items[2].startswith("ITEM_"):
                continue

            index = int(items[2])

            item_strings[index] = items[1]

            if index > max_value:
                max_value = index

        ordered_index = collections.OrderedDict(sorted(item_strings.items()))

        for index in range(max_value):
            if not ordered_index.__contains__(index):
                _items.append(None)
                continue
            item = ordered_index[index]

            split = item.split("_")

            first = True

            for i in split:
                if first:
                    first = False
                    item = i[0] + i[1:].lower()
                    continue

                item += " " + i[0] + i[1:].lower()

            if not game_strings.has_item(item):
                translations.add_translation(_items_prefix + game_strings.clean_up(item), item)

                _items.append(_items_prefix + game_strings.clean_up(item))
            else:
                _items.append("pokemon.item." + game_strings.clean_up(item))

def generate():
    print("Generating Items")

    write_file(
        os.path.join(directories.get_output_dir("emerald_imperium", True),
                     "emeraldImperium.items"), {"items": _items})

def get_item_string(input: str) -> str | None:
    for item in _items:
        if item is None:
            continue
        if item.lower().endswith(input.lower()):
            return item

    return None