import os
import re

import pokelink.directories as directories
from pokelink.json_output import write_file

_exp_growth: list = []


def process():
    print("Processing Exp")
    global _exp_growth

    path = os.path.join(directories.get_external_dir("pokemon-unknown"),
                        "cfru", "src", "Tables", "experience_tables.c")
    with open(path, "r") as f:
        content = f.read()

    start = content.index("const u32 gExperienceTables")
    outer = content[start:]

    _exp_growth = []
    for block in re.finditer(r'\{[^{}]*//GROWTH_[^{}]*\}', outer, re.DOTALL):
        nums = [int(n) for n in re.findall(r'\d+', block.group())]
        _exp_growth.append(nums)

    assert len(_exp_growth) == 6, f"Expected 6 growth curves, got {len(_exp_growth)}"
    for i, curve in enumerate(_exp_growth):
        assert len(curve) == 255, f"Growth curve {i} has {len(curve)} entries, expected 255"


def generate():
    print("Generating Exp")
    write_file(
        os.path.join(directories.get_output_dir("pokemon-unknown/v1.6/", True), "unknown.exp"),
        {"expGrowth": _exp_growth}
    )
