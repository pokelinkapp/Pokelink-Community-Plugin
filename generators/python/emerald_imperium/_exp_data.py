import pokelink.gen3.poke_math as poke_math
import pokelink.directories as directories
import os

from pokelink import strip_comments
from pokelink.json_output import write_file

growth_indexes = {
    "GROWTH_MEDIUM_FAST": 0,
    "GROWTH_ERRATIC": 1,
    "GROWTH_FLUCTUATING": 2,
    "GROWTH_MEDIUM_SLOW": 3,
    "GROWTH_FAST": 4,
    "GROWTH_SLOW": 5
}


def generate():
    print("Generating EXP Tables")

    tables = []
    found = False
    skip_first_bracket = True
    with open(os.path.join(directories.get_external_dir("emerald-imperium"),
                           "src", "data", "pokemon", "experience_tables.h"),
              "r") as file:
        table = []
        table_text = ""
        is_reading = False
        for line in file:
            if line.__contains__("gExperienceTables["):
                found = True
                continue

            if not found:
                continue

            if line.__contains__("{"):
                if skip_first_bracket:
                    skip_first_bracket = False
                    continue
                table = []
                table_text = ""
                is_reading = True
            elif line.__contains__("}"):
                if not is_reading:
                    continue
                temp_table = [strip_comments(value) for value in table_text.split(",")]

                for entry in temp_table:
                    if entry == "":
                        continue
                    if entry.startswith("EXP_SLOW("):
                        table.append(poke_math.EXP_SLOW((int(entry.removeprefix(
                            "EXP_SLOW(").removesuffix(")")))))
                        continue
                    if entry.startswith("EXP_FAST("):
                        table.append(poke_math.EXP_FAST((int(entry.removeprefix(
                            "EXP_FAST(").removesuffix(")")))))
                        continue
                    if entry.startswith("EXP_MEDIUM_FAST("):
                        table.append(poke_math.EXP_MEDIUM_FAST((
                            int(entry.removeprefix(
                                "EXP_MEDIUM_FAST(").removesuffix(
                                ")")))))
                        continue
                    if entry.startswith("EXP_MEDIUM_SLOW("):
                        table.append(poke_math.EXP_MEDIUM_SLOW((
                            int(entry.removeprefix(
                                "EXP_MEDIUM_SLOW(").removesuffix(
                                ")")))))
                        continue
                    if entry.startswith("EXP_ERRATIC("):
                        table.append(poke_math.EXP_ERRATIC((
                            int(entry.removeprefix(
                                "EXP_ERRATIC(").removesuffix(
                                ")")))))
                        continue
                    if entry.startswith("EXP_FLUCTUATING("):
                        table.append(poke_math.EXP_FLUCTUATING((
                            int(entry.removeprefix(
                                "EXP_FLUCTUATING(").removesuffix(
                                ")")))))
                        continue
                    table.append(int(entry))

                tables.append(table)

                if tables.__len__() == 6:
                    break
            else:
                table_text += line

    output = {"expGrowth": tables}

    write_file(os.path.join(directories.get_output_dir("emerald_imperium", True), "emeraldImperium.exp"), output)
