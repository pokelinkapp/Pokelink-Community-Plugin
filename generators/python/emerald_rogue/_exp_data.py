import pokelink.directories as directories
import os

from emerald_rogue import RogueVersion
from pokelink.json_output import write_file


def generate(version: RogueVersion):
    print("Generating EXP Tables")

    tables = []

    exp_table = []

    for i in range(101):
        exp_table.append(i * 300)

    for i in range(6):
        tables.append(exp_table)

    output = {"expGrowth": tables}

    write_file(os.path.join(directories.get_output_dir("emerald_rogue" + "/" + (
        "vanilla" if version == RogueVersion.VANILLA else "expansion"), True),
                            "emeraldRogue.exp"), output)
