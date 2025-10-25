import pokelink.directories as directories
import pokelink.translations as translations

from pokelink import strip_comments, game_strings
from pokelink.json_output import write_file

import os

_move_ids = dict()
_move_counts = dict()
_after_equations = dict()
_moves = []

def get_move_number(line: str) -> int:
    return int(line.split(" ")[-1].removesuffix(","))

def process():
    global _after_equations
    print("Processing Moves")

    with open(os.path.join(directories.get_external_dir("emerald-imperium"),
                           "include", "constants", "moves.h"), "r") as file:
        move_lines = [strip_comments(line) for line in file]

        for line in move_lines:
            if not line:
                continue

            if line.startswith("#define MOVE_UNAVAILABLE"):
                break

            items = line.split(" ")

            if line.startswith("#define LAST_MAX_MOVE"):
                for id in _after_equations.keys():
                    index = 0
                    for part in _after_equations[id]:
                        if _move_counts.__contains__(part):
                            index += _move_counts[part]
                            continue

                        if _move_ids.__contains__(part):
                            index += _move_ids[part]
                            continue

                        index += int(part)

                    _move_ids[id] = index
                _after_equations = dict()

            if line.startswith("#define MOVES_COUNT") or line.startswith(
                    "#define FIRST_") or line.startswith("#define LAST_"):
                if _move_counts.__contains__(items[-1]):
                    _move_counts[items[1]] = _move_counts[items[-1]]
                elif _move_ids.__contains__(items[-1]):
                    _move_counts[items[1]] = _move_ids[items[-1]]
                elif items[-1].endswith(")"):
                    equation = str.join("", items[2:]).strip()

                    if not equation.startswith("(") or not equation.endswith(
                            ")"):
                        continue

                    equation = equation[1:-1].replace(" ", "")
                    equation_parts = equation.split("+")

                    index = 0

                    for part in equation_parts:
                        if _move_counts.__contains__(part):
                            index += _move_counts[part]
                            continue

                        index += int(part)
                    _move_counts[items[1]] = index
                else:
                    _move_counts[items[1]] = int(items[-1])

            if not line.startswith("#define MOVE_"):
                continue

            if items[1] == "MOVE_NONE":
                continue

            if items[-1].startswith("MOVE_"):
                if not _move_ids.__contains__(items[-1]):
                    print(
                        f"\tWARNING: Unable to find move definition {items[-1]}")
                else:
                    _move_ids[items[1]] = _move_ids[items[-1]]
                continue

            if items[-1].endswith(")"):
                equation = str.join("", items[2:]).strip()

                if not equation.startswith("(") or not equation.endswith(")"):
                    continue

                equation = equation[1:-1].replace(" ", "")
                equation_parts = equation.split("+")

                index = 0

                store_equation = False

                for part in equation_parts:
                    if _move_counts.__contains__(part):
                        index += _move_counts[part]
                        continue

                    if _move_ids.__contains__(part):
                        index += _move_ids[part]
                        continue

                    if part.isdigit():
                        index += int(part)
                    else:
                        store_equation = True

                if store_equation:
                    _after_equations[items[1]] = equation_parts
                    continue

            else:
                index = int(items[-1])

            _move_ids[items[1]] = index

    print(f"\t{_move_ids.__len__():n} moves found")


def generate():
    print("Generating Moves")

    with open(os.path.join(directories.get_external_dir("emerald-imperium"),
                           "src", "data", "moves_info.h")) as file:

        reading = False
        current_move = dict()
        current_name: str | None = None

        for line in [strip_comments(line) for line in file]:
            if line.startswith("{"):
                continue

            if line.startswith("}") and reading:
                reading = False
                _moves.append(current_move)
                current_name = None
                continue

            if not line.startswith("[MOVE_"):
                if not reading:
                    continue

                if line.startswith(".accuracy"):
                    current_move["accuracy"] = get_move_number(line)
                elif line.startswith(".power"):
                    current_move["power"] = get_move_number(line)
                elif line.startswith(".pp"):
                    current_move["pp"] = get_move_number(line)
                elif line.startswith(".type"):
                    type_name = line.split(" ")[-1].removeprefix("TYPE_").removesuffix(",")
                    current_move["type"] = f"pokemon.type.{game_strings.clean_up(type_name)}"
                elif line.startswith(".priority"):
                    current_move["priority"] = get_move_number(line)
                elif line.startswith(".category"):
                    category = line.split(" ")[-1].removeprefix("DAMAGE_CATEGORY_").removesuffix(",")
                    current_move["category"] = f"pokemon.category.move.{game_strings.clean_up(category)}"
            else:
                if line.endswith("] ="):
                    move_id = line.removeprefix("[MOVE_").removesuffix("] =")
                    current_name = move_id.removeprefix("G_")
                    current_move = {}

                    if current_name == "NONE":
                        continue

                    if not _move_ids.__contains__(f"MOVE_{move_id}"):
                        print(f"\tWARNING: Unknown move {move_id}")
                        continue

                    current_move["id"] = _move_ids[f"MOVE_{move_id}"]

                    if game_strings.has_move(current_name):
                        current_move["name"] = f"pokemon.move.{game_strings.clean_up(current_name)}"
                    else:

                        split = current_name.split("_")

                        first = True

                        item = ""

                        for i in split:
                            if first:
                                first = False
                                item = i[0] + i[1:].lower()
                                continue

                            item += " " + i[0] + i[1:].lower()

                        current_move["name"] = f"EmeraldImperium.Move.{game_strings.clean_up(current_name)}"
                        translations.add_translation(current_move["name"], item)
                    reading = True
                    continue


    write_file(
        os.path.join(directories.get_output_dir("emerald_imperium", True),
                     "emeraldImperium.moves"), _moves)
