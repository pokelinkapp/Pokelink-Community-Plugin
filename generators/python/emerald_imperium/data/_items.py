import pokelink.directories as directories
import pokelink.translations as translations

from pokelink import strip_comments, game_strings
from pokelink.json_output import write_file

import os
import collections

_items = []

_items_prefix = "EmeraldImperium.Item."

def process():
    print("Processing Items")

    item_strings = dict()

    with open(os.path.join(directories.get_external_dir("emerald-imperium"),
                           "include", "constants", "items.h"), "r") as file:
        item_lines = [strip_comments(line) for line in file]

        for line in item_lines:
            if not line:
                continue

            if line.startswith("#define ITEMS_COUNT"):
                break

            if not line.startswith("#define ITEM_") or line.endswith("0xFFFF"):
                continue


            items = line.replace("ITEM_", "", 1).split(" ")

            if items[2].startswith("ITEM_"):
                item_strings[items[1]] = item_strings[items[2]]
                continue

            index = int(items[2])

            item_strings[items[1]] = index

        ordered_index = collections.OrderedDict(sorted(item_strings.items()))

        for index in ordered_index:
            item = index

            split = item.split("_")

            first = True

            for i in split:
                if first:
                    first = False
                    item = i[0] + i[1:].lower()
                    continue

                item += " " + i[0] + i[1:].lower()


            translations.add_translation(_items_prefix + game_strings.clean_up(item), item)

            _items.append(_items_prefix + game_strings.clean_up(item))

def generate():
    print("Generating Items")

    write_file(
        os.path.join(directories.get_output_dir("emerald_imperium", True),
                     "items.py.json"), {"items": _items})