import pokelink.directories as directories
import pokelink.translations as translations
from emerald_rogue import RogueVersion

from pokelink import strip_comments, game_strings
from pokelink.json_output import write_file

import os
import collections

_items = []

_items_prefix = "EmeraldRogue.Item."


def process(version: RogueVersion):
    _items.clear()
    print("Processing Items")

    item_strings = dict()

    with open(os.path.join(directories.get_external_dir("emerald-rogue"),
                           "vanilla" if version == RogueVersion.VANILLA else "expansion",
                           "include",
                           "constants", "items.h"), "r") as file:
        item_lines = [strip_comments(line) for line in file]

        max_value = 0

        for line in item_lines:
            if not line:
                continue

            if line.startswith("#define ITEMS_COUNT"):
                break

            if not line.startswith("#define ITEM_") or line.startswith(
                    "#define ITEM_NONE") or line.endswith("0xFFFF"):
                continue

            items = line.replace("ITEM_", "", 1).split(" ")

            if items[2].startswith("ITEM_"):
                continue

            index = int(items[2])

            item_strings[index] = items[1]

            if index > max_value:
                max_value = index

            if index == (376 if version == RogueVersion.VANILLA else 826):
                break

        if version == RogueVersion.EXPANSION:
            max_value = 827
            item_strings[max_value] = "LINK_CABLE"
            max_value += 1
            item_strings[max_value] = "QUEST_LOG"
            max_value += 1
            item_strings[max_value] = "HEALING_FLASK"
            max_value += 1
            item_strings[max_value] = "BASIC_RIDING_WHISTLE"
            max_value += 1
            item_strings[max_value] = "GOLD_RIDING_WHISTLE"
            max_value += 1
            item_strings[max_value] = "C_GEAR"
            max_value += 1
            item_strings[max_value] = "DAYCARE_PHONE"
            max_value += 1
            item_strings[max_value] = "BUILDING_SUPPLIES"
            max_value += 1
            item_strings[max_value] = "ALOLA_STONE"
            max_value += 1
            item_strings[max_value] = "GALAR_STONE"
            max_value += 1
            item_strings[max_value] = "HISUI_STONE"
            max_value += 1
            item_strings[max_value] = "SMALL_COIN_CASE"
            max_value += 1
            item_strings[max_value] = "LARGE_COIN_CASE"
            max_value += 1
            item_strings[max_value] = "GOLDEN_SEED"
            max_value = 839

            item_strings[max_value] = "POKEBLOCK_NORMAL"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_FIGTHING"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_FLYING"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_POISON"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_GROUND"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_ROCK"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_BUG"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_GHOST"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_STEEL"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_FIRE"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_WATER"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_GRASS"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_ELECTRIC"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_PSYCHIC"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_ICE"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_DRAGON"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_DARK"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_FAIRY"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_SHINY"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_HP"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_ATTACK"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_DEFENCE"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_SPEED"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_SPECIAL_ATTACK"
            max_value += 1
            item_strings[max_value] = "POKEBLOCK_SPECIAL_DEFENCE"
            max_value += 1

        ordered_index = collections.OrderedDict(sorted(item_strings.items()))

        for index in range(max_value):
            if not ordered_index.__contains__(index):
                _items.append(None)
                continue
            item = ordered_index[index]

            split = item.split("_")

            if split[-1].__len__() < 4 and split[-1] != "POT":
                _items.append(None)
                continue

            first = True

            for i in split:
                if first:
                    first = False
                    item = i[0] + i[1:].lower()
                    continue

                item += " " + i[0] + i[1:].lower()

            if not game_strings.has_item(item):
                translations.add_translation(
                    _items_prefix + game_strings.clean_up(item), item)

                _items.append(_items_prefix + game_strings.clean_up(item))
            else:
                _items.append("pokemon.item." + game_strings.clean_up(item))


def generate(version: RogueVersion):
    print("Generating Items")

    write_file(
        os.path.join(directories.get_output_dir("emerald_rogue" + "/" + (
            "vanilla" if version == RogueVersion.VANILLA else "expansion"),
                                                True),
                     "emeraldRogue.items"), {"items": _items})

def get_item_string(input: str) -> str | None:
    for item in _items:
        if item is None:
            continue
        if item.lower().endswith(input.lower()):
            return item

    return None