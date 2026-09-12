import os

import pokelink.directories as directories
import pokelink.translations as translations
from pokelink import game_strings
from pokelink.json_output import write_file

_PREFIX = "PokemonUnknown.Move."
_moves = []
_move_name_by_constant: dict = {}

_DISPLAY_OVERRIDES = {
    "VICEGRIP":  "Vise Grip",
    "LEECHFANG": "Leech Fang",
    "STEELYHIT": "Steely Hit",
    "CIPHER":    "Cipher",
}


def _parse_ids() -> dict:
    ids = {}
    with open(os.path.join(directories.get_external_dir("pokemon-unknown"),
                           "cfru", "include", "constants", "moves.h"), "r") as f:
        for line in f:
            line = line.split("//")[0].strip()
            if not line.startswith("#define MOVE_"):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            name = parts[1].removeprefix("MOVE_")
            if name in ("NONE", "NAME_LENGTH"):
                continue
            try:
                ids[name] = int(parts[2], 16)
            except ValueError:
                pass
    return ids


def _parse_battle_moves() -> dict:
    result = {}
    current_move = None
    current_data = {}
    in_block = False

    with open(os.path.join(directories.get_external_dir("pokemon-unknown"),
                           "cfru", "src", "Tables", "battle_moves.c"), "r") as f:
        for line in f:
            line = line.split("//")[0].strip()
            if not line:
                continue

            if line.startswith("[MOVE_") and "]" in line:
                name = line[line.index("[") + 1:line.index("]")].removeprefix("MOVE_")
                current_move = name if name != "NONE" else None
                current_data = {}
                continue

            if "{" in line:
                if current_move is not None and not in_block:
                    in_block = True
                continue

            if "}" in line:
                if in_block and current_move:
                    result[current_move] = current_data
                in_block = False
                current_move = None
                continue

            if not in_block or not line.startswith("."):
                continue

            parts = line.lstrip(".").split("=", 1)
            if len(parts) < 2:
                continue

            field = parts[0].strip()
            value = parts[1].strip().rstrip(",").strip()

            if field == "power":
                current_data["power"] = int(value)
            elif field == "accuracy":
                current_data["accuracy"] = int(value)
            elif field == "pp":
                current_data["pp"] = int(value)
            elif field == "priority":
                current_data["priority"] = int(value)
            elif field == "type":
                current_data["type"] = value
            elif field == "split":
                current_data["split"] = value

    return result


def process():
    print("Processing Moves")
    global _moves, _move_name_by_constant

    move_lookup = {
        ca.replace("_", ""): ca
        for ca in game_strings._game_strings.get("en", {}).get("clean_moves", [])
    }

    ids = _parse_ids()
    battle_data = _parse_battle_moves()

    entries = {}
    for name, data in battle_data.items():
        if name not in ids:
            continue
        move_id = ids[name]

        if name in _DISPLAY_OVERRIDES:
            display = _DISPLAY_OVERRIDES[name]
        else:
            display = None

        if display is not None and game_strings.has_move(display):
            move_name = "pokemon.move." + game_strings.clean_up(display)
        else:
            lookup_key = name.lower().replace("_", "")
            if lookup_key in move_lookup:
                move_name = "pokemon.move." + move_lookup[lookup_key]
            else:
                if display is None:
                    display = " ".join(p[0].upper() + p[1:].lower() for p in name.split("_"))
                    print(f"\tWARNING: No Pokelink translation for move {display}")
                key = _PREFIX + game_strings.clean_up(display)
                translations.add_translation(key, display)
                move_name = key

        _move_name_by_constant[name] = move_name

        split = data.get("split", "SPLIT_STATUS")
        entries[move_id] = {
            "id": move_id,
            "name": move_name,
            "power": data.get("power", 0),
            "type": "pokemon.type." + data.get("type", "TYPE_NORMAL").removeprefix("TYPE_").lower(),
            "accuracy": data.get("accuracy", 0),
            "pp": data.get("pp", 0),
            "priority": data.get("priority", 0),
            "category": "pokemon.category.move." + split.removeprefix("SPLIT_").lower(),
        }

    _moves = [entries[k] for k in sorted(entries)]


def generate():
    print("Generating Moves")
    write_file(
        os.path.join(directories.get_output_dir("pokemon-unknown/v1.6/", True), "unknown.moves"),
        _moves
    )


def get_move_by_constant(constant: str) -> str:
    return _move_name_by_constant.get(constant, "")
