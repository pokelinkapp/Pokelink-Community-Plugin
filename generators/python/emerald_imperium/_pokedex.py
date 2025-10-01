import pokelink.proto.v0_7_1.pokedex_pb2 as pb_pokedex
import pokelink.directories as directories
from google.protobuf import json_format

from pokelink import strip_comments, game_strings
from pokelink.gen3 import poke_math
from pokelink.json_output import write_file

import os

_dex = pb_pokedex.Pokedex()

_dex.version = "0.7.1"

_species_form_name = {}
_dex_ids = {}
_stats = {}

_growth_indexes = {
    "GROWTH_MEDIUM_FAST": 0,
    "GROWTH_ERRATIC": 1,
    "GROWTH_FLUCTUATING": 2,
    "GROWTH_MEDIUM_SLOW": 3,
    "GROWTH_FAST": 4,
    "GROWTH_SLOW": 5
}


def process_species_forms():
    global _species_form_name
    print("\tProcessing Species and Forms")
    with open(os.path.join(directories.get_external_dir("emerald-imperium"),
                           "include", "constants", "species.h"), "r") as file:

        internal_lines = [strip_comments(line) for line in file]

        for line in internal_lines:
            if not line:
                continue

            if not line.startswith("#define SPECIES_"):
                continue

            if line.startswith("#define SPECIES_NONE") or line.startswith(
                    "#define SPECIES_EGG"):
                continue

            items = line.split(" ")

            species = items[1].removeprefix("SPECIES_")

            if items[-1].startswith("SPECIES"):
                continue

            internal_id = int(items[-1])

            _species_form_name[internal_id] = species

        print(
            f"\t\tFound {_species_form_name.__len__():n} species/form entries")


def process_national_dex_ids():
    global _dex_ids
    print("\tProcessing National Dex IDs")
    with open(os.path.join(directories.get_external_dir("emerald-imperium"),
                           "include", "constants", "pokedex.h"), "r") as file:

        internal_lines = [strip_comments(line) for line in file]

        dex_id = 1

        for line in internal_lines:
            if not line:
                continue

            if not line.startswith("NATIONAL_DEX_"):
                continue

            if line.startswith("NATIONAL_DEX_NONE"):
                continue

            species = line.removeprefix("NATIONAL_DEX").removesuffix(",")

            _dex_ids[species] = dex_id
            dex_id += 1

        print(f"\t\tFound {_dex_ids.__len__():n} dex ids")


def get_pokemon_number(line: str) -> int:
    return int(line.split(" ")[-1].removesuffix(","))


def process_species_stats():
    global _stats
    print("\tProcessing Stats")

    lines = []

    for info in [
        "species_info/gen_1_families.h", "species_info/gen_2_families.h",
        "species_info/gen_3_families.h", "species_info/gen_4_families.h",
        "species_info/gen_5_families.h", "species_info/gen_6_families.h",
        "species_info/gen_7_families.h", "species_info/gen_8_families.h",
        "species_info/gen_9_families.h", "species_info.h"
    ]:
        with open(os.path.join(directories.get_external_dir("emerald-imperium"),
                               "src", "data", "pokemon", info), "r") as file:
            lines += [strip_comments(line) for line in file]

    reading = False
    current_pokemon: pb_pokedex.Species | None = None
    current_name: str | None = None

    for line in lines:
        if line.startswith("{"):
            continue

        if line.startswith("}"):
            reading = False
            _stats[current_name] = current_pokemon
            continue

        if not line.startswith("[SPECIES_"):
            if not reading:
                continue

            if line.startswith(".baseHP"):
                current_pokemon.baseStats.hp = get_pokemon_number(line)
            elif line.startswith(".baseAttack"):
                current_pokemon.baseStats.attack = get_pokemon_number(line)
            elif line.startswith(".baseDefense"):
                current_pokemon.baseStats.defense = get_pokemon_number(line)
            elif line.startswith(".baseSpAttack"):
                current_pokemon.baseStats.specialAttack = get_pokemon_number(
                    line)
            elif line.startswith(".baseSpDefense"):
                current_pokemon.baseStats.specialDefense = get_pokemon_number(
                    line)
            elif line.startswith(".baseSpeed"):
                current_pokemon.baseStats.speed = get_pokemon_number(line)
            elif line.startswith(".types"):
                types = line.removeprefix(".types = MON_TYPES(").removesuffix(
                    "),").split(", ")

                for type in types:
                    current_pokemon.types.append(
                        f"pokemon.type.{type.lower().removeprefix("type_")}")
            elif line.startswith(".catchRate"):
                current_pokemon.catchRate = get_pokemon_number(line)
            elif line.startswith(".evYield_HP"):
                current_pokemon.evYield.hp = get_pokemon_number(line)
            elif line.startswith(".evYield_Attack"):
                current_pokemon.evYield.attack = get_pokemon_number(line)
            elif line.startswith(".evYield_Defense"):
                current_pokemon.evYield.defense = get_pokemon_number(line)
            elif line.startswith(".evYield_SpAttack"):
                current_pokemon.evYield.specialAttack = get_pokemon_number(line)
            elif line.startswith(".evYield_SpDefense"):
                current_pokemon.evYield.specialDefense = get_pokemon_number(
                    line)
            elif line.startswith(".evYield_Speed"):
                current_pokemon.evYield.speed = get_pokemon_number(line)
            elif line.startswith(".genderRatio"):
                value = line.split(" ")[-1].removesuffix(",")

                if value == "MON_GENDERLESS":
                    current_pokemon.genderRatio = 255
                    continue
                if value == "MON_FEMALE":
                    current_pokemon.genderRatio = 254
                    continue
                if value == "MON_MALE":
                    current_pokemon.genderRatio = 0
                    continue

                current_pokemon.genderRatio = poke_math.PERCENT_FEMALE(float(
                    value.removeprefix("PERCENT_FEMALE(").removesuffix(")")))
            elif line.startswith(".eggCycles"):
                current_pokemon.hatchCycles = int(line.split(" ")[-1].removesuffix(","))
            elif line.startswith(".growthRate"):
                key = line.split(" ")[-1].removesuffix(",")
                if not _growth_indexes.__contains__(key):
                    print(f"ERROR Unable to read {current_name}'s growth rate. Recieved value: {key}")
                    exit(2)

                current_pokemon.growthRate = _growth_indexes[key]
            elif line.startswith(".abilities"):
                abilities = line.removeprefix(".abilities = {").removesuffix("},").split(", ")

                for ability in abilities:
                    ability = ability.strip()
                    if ability == "ABILITY_NONE":
                        current_pokemon.abilities.append("")
                        continue
                    if not game_strings.has_ability(ability.removeprefix("ABILITY_")):
                        current_pokemon.abilities.append(f"EmeraldImperium.Ability.{game_strings.clean_up(ability.removeprefix("ABILITY_"))}")
                    else:
                        current_pokemon.abilities.append(f"pokemon.ability.{game_strings.clean_up(ability.removeprefix("ABILITY_"))}")
        else:
            if line.endswith("] ="):
                current_name = line.removeprefix("[SPECIES_").removesuffix(
                    "] =")
                current_pokemon = pb_pokedex.Species()
                reading = True
            continue


def process():
    print("Processing Pokedex")
    process_species_forms()
    process_national_dex_ids()
    process_species_stats()


def generate():
    print("Generating Pokedex")

    write_file(
        os.path.join(directories.get_output_dir("emerald_imperium", True),
                     "emeraldImperium.dex"), json_format.MessageToDict(_dex))
