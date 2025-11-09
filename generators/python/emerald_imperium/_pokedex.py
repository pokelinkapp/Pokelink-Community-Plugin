import collections

import pokelink.proto.v0_7_1.pokedex_pb2 as pb_pokedex
import pokelink.directories as directories
import pokelink.translations as translations
from google.protobuf import json_format

from emerald_imperium._items import get_item_string
from emerald_imperium._moves import get_move_string
from pokelink import strip_comments, game_strings
from pokelink.gen3 import poke_math
from pokelink.json_output import write_file

import os

_dex = pb_pokedex.Pokedex()

_dex.version = "0.7.1"

_species_form_id = dict()
_species_forms = dict()
_evolutions = dict()
_dex_ids = dict()
_stats = dict()

_growth_indexes = {
    "GROWTH_MEDIUM_FAST": 0,
    "GROWTH_ERRATIC": 1,
    "GROWTH_FLUCTUATING": 2,
    "GROWTH_MEDIUM_SLOW": 3,
    "GROWTH_FAST": 4,
    "GROWTH_SLOW": 5
}


def process_species_forms():
    global _species_form_id
    print("\tProcessing Species and Forms")
    with (open(os.path.join(directories.get_external_dir("emerald-imperium"),
                            "include", "constants", "species.h"), "r") as file):

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

            _species_form_id[species] = internal_id

            if not game_strings.has_species(
                    species) and species != "NIDORAN_F" and species != "NIDORAN_M" and species != "TYPE_NULL" and species != "MR_MIME_GALAR" and species != "MIME_JR":
                split = species.split("_")
                mon = split[0]
                form = str.join("_", split[1:])

                if not _species_forms.__contains__(mon):
                    _species_forms[mon] = dict()
                    _species_forms[mon][form] = 0
                else:
                    _species_forms[mon][form] = len(_species_forms[mon])
            elif species == "MR_MIME_GALAR":
                split = species.split("_")
                mon = str.join("_", split[:2])
                form = str.join("_", split[2:])

                if not _species_forms.__contains__(mon):
                    _species_forms[mon] = dict()
                    _species_forms[mon]["_"] = 0
                else:
                    _species_forms[mon][form] = len(_species_forms[mon])
            else:
                if not _species_forms.__contains__(species):
                    _species_forms[species] = dict()
                    _species_forms[species]["_"] = 0
                else:
                    _species_forms[species]["_"] = len(_species_forms[species])

        print(
            f"\t\tFound {_species_form_id.__len__():n} species/form entries")


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

            species = line.removeprefix("NATIONAL_DEX_").removesuffix(",")

            _dex_ids[dex_id] = species
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
    reading_evolutions = False
    current_evos = []
    current_pokemon: pb_pokedex.Species | None = None
    current_name: str | None = None

    for line in lines:
        line = line.strip()
        if line.startswith("{"):
            if reading_evolutions:
                evos = line.split(",")

                for i in range(evos.__len__()):
                    evos[i] = evos[i].removeprefix("{").removesuffix(
                        ")").removesuffix("}").strip().removeprefix("SPECIES_")

                if evos[-1] == "":
                    evos.pop(-1)

                current_evos.append(evos)

                if line.endswith("),"):
                    reading_evolutions = False

                    if not _evolutions.__contains__(current_name):
                        _evolutions[current_name] = []
                    _evolutions[current_name].extend(current_evos)

                    current_evos = []
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
                current_pokemon.hatchCycles = int(
                    line.split(" ")[-1].removesuffix(","))
            elif line.startswith(".friendship"):
                value = line.split(" ")[-1].removesuffix(",")

                if value == "STANDARD_FRIENDSHIP":
                    current_pokemon.baseFriendship = 70
                else:
                    current_pokemon.baseFriendship = int(value)
            elif line.startswith(".growthRate"):
                key = line.split(" ")[-1].removesuffix(",")
                if not _growth_indexes.__contains__(key):
                    print(
                        f"ERROR Unable to read {current_name}'s growth rate. Recieved value: {key}")
                    exit(2)

                current_pokemon.growthRate = _growth_indexes[key]
            elif line.startswith(".abilities"):
                abilities = line.removeprefix(".abilities = {").removesuffix(
                    "},").split(", ")

                for ability in abilities:
                    ability = ability.strip()
                    if ability == "ABILITY_NONE":
                        current_pokemon.abilities.append("")
                        continue
                    if not game_strings.has_ability(
                            ability.removeprefix("ABILITY_")):
                        current_pokemon.abilities.append(
                            f"EmeraldImperium.Ability.{game_strings.clean_up(ability.removeprefix("ABILITY_"))}")
                    else:
                        current_pokemon.abilities.append(
                            f"pokemon.ability.{game_strings.clean_up(ability.removeprefix("ABILITY_"))}")
            elif line.startswith(".evolutions = EVOLUTION({"):
                if not line.endswith("),"):
                    reading_evolutions = True

                evoSpecs = line.removeprefix(".evolutions = EVOLUTION({").split(
                    ",")

                for i in range(evoSpecs.__len__()):
                    evoSpecs[i] = evoSpecs[i].removesuffix(")").removesuffix(
                        "}").strip().removeprefix("SPECIES_")

                if evoSpecs[-1] == "":
                    evoSpecs.pop(-1)

                current_evos.append(evoSpecs)

                if not reading_evolutions:
                    if not _evolutions.__contains__(current_name):
                        _evolutions[current_name] = []
                    _evolutions[current_name].extend(current_evos)

                    current_evos = []

        else:
            if line.endswith("] =") or line.endswith("]   ="):
                current_name = line.removeprefix("[SPECIES_").removesuffix(
                    "] =").removesuffix("]   =")
                current_pokemon = pb_pokedex.Species()
                reading = True
            continue

    unown_stat = pb_pokedex.Species()
    unown_stat.baseStats.hp = 48
    unown_stat.baseStats.attack = 48
    unown_stat.baseStats.defense = 48
    unown_stat.baseStats.speed = 96
    unown_stat.baseStats.specialAttack = 96
    unown_stat.baseStats.specialDefense = 48
    unown_stat.types.append("pokemon.type.psychic")
    unown_stat.catchRate = 255
    unown_stat.evYield.attack = 1
    unown_stat.evYield.specialAttack = 1
    unown_stat.genderRatio = 255
    unown_stat.hatchCycles = 40
    unown_stat.baseFriendship = 70
    unown_stat.growthRate = 0
    unown_stat.abilities.append("pokemon.ability.levitate")
    unown_stat.abilities.append("")
    unown_stat.abilities.append("pokemon.ability.simple")

    _stats["UNOWN"] = unown_stat

    for form in "B|C|D|E|F|G|H|I|J|K|L|M|N|O|P|Q|R|S|T|U|V|W|X|Y|Z".split(
            "|") + [
                    "EXCLAMATION", "QUESTION"
                ]:
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(unown_stat)
        _stats[f"UNOWN_{form}"] = form_stat

    mothim_stat = pb_pokedex.Species()
    mothim_stat.baseStats.hp = 70
    mothim_stat.baseStats.attack = 84
    mothim_stat.baseStats.defense = 50
    mothim_stat.baseStats.speed = 80
    mothim_stat.baseStats.specialAttack = 94
    mothim_stat.baseStats.specialDefense = 50
    mothim_stat.types.append("pokemon.type.bug")
    mothim_stat.types.append("pokemon.type.flying")
    mothim_stat.catchRate = 45
    mothim_stat.evYield.attack = 1
    mothim_stat.evYield.specialAttack = 1
    mothim_stat.genderRatio = 0
    mothim_stat.hatchCycles = 15
    mothim_stat.baseFriendship = 70
    mothim_stat.growthRate = 0
    mothim_stat.abilities.append("pokemon.ability.swarm")
    mothim_stat.abilities.append("")
    mothim_stat.abilities.append("pokemon.ability.tinted_lens")

    for form in ["PLANT", "SANDY", "TRASH"]:
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(mothim_stat)
        _stats["MOTHIM_" + form] = form_stat
        if form == "PLANT":
            _stats["MOTHIM"] = form_stat

    arceus_stat = pb_pokedex.Species()
    arceus_stat.baseStats.hp = 120
    arceus_stat.baseStats.attack = 120
    arceus_stat.baseStats.defense = 120
    arceus_stat.baseStats.speed = 120
    arceus_stat.baseStats.specialAttack = 120
    arceus_stat.baseStats.specialDefense = 120
    arceus_stat.catchRate = 43
    arceus_stat.evYield.hp = 3
    arceus_stat.genderRatio = 255
    arceus_stat.hatchCycles = 120
    arceus_stat.baseFriendship = 0
    arceus_stat.growthRate = 5
    arceus_stat.abilities.append("pokemon.ability.multitype")
    arceus_stat.abilities.append("")
    arceus_stat.abilities.append("")

    for p_type in [
        "NORMAL", "FIGHTING", "FLYING", "POISON", "GROUND", "ROCK", "BUG",
        "GHOST", "STEEL", "FIRE", "WATER", "GRASS", "ELECTRIC", "PSYCHIC",
        "ICE", "DRAGON", "DARK", "FAIRY"
    ]:
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(arceus_stat)
        form_stat.types.append("pokemon.type." + p_type.lower())
        _stats["ARCEUS_" + p_type] = form_stat

    genesect_stat = pb_pokedex.Species()
    genesect_stat.baseStats.hp = 71
    genesect_stat.baseStats.attack = 120
    genesect_stat.baseStats.defense = 95
    genesect_stat.baseStats.speed = 99
    genesect_stat.baseStats.specialAttack = 120
    genesect_stat.baseStats.specialDefense = 95
    genesect_stat.types.append("pokemon.type.bug")
    genesect_stat.types.append("pokemon.type.steel")
    genesect_stat.catchRate = 3
    genesect_stat.evYield.attack = 1
    genesect_stat.evYield.speed = 1
    genesect_stat.evYield.specialAttack = 1
    genesect_stat.genderRatio = 255
    genesect_stat.hatchCycles = 120
    genesect_stat.baseFriendship = 0
    genesect_stat.growthRate = 5
    genesect_stat.abilities.append("pokemon.ability.download")
    genesect_stat.abilities.append("")
    genesect_stat.abilities.append("")

    _stats["GENESECT"] = genesect_stat

    for form in ["DOUSE", "SHOCK", "BURN", "CHILL"]:
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(genesect_stat)
        _stats["GENESECT_" + form] = form_stat

    scatterbug_stat = pb_pokedex.Species()
    scatterbug_stat.baseStats.hp = 38
    scatterbug_stat.baseStats.attack = 35
    scatterbug_stat.baseStats.defense = 40
    scatterbug_stat.baseStats.speed = 35
    scatterbug_stat.baseStats.specialAttack = 27
    scatterbug_stat.baseStats.specialDefense = 25
    scatterbug_stat.types.append("pokemon.type.bug")
    scatterbug_stat.catchRate = 255
    scatterbug_stat.evYield.defense = 1
    scatterbug_stat.genderRatio = poke_math.PERCENT_FEMALE(50)
    scatterbug_stat.hatchCycles = 15
    scatterbug_stat.baseFriendship = 70
    scatterbug_stat.growthRate = 0
    scatterbug_stat.abilities.append("pokemon.ability.shield_dust")
    scatterbug_stat.abilities.append("pokemon.ability.compound_eyes")
    scatterbug_stat.abilities.append("pokemon.ability.friend_guard")

    spewpa_stat = pb_pokedex.Species()
    spewpa_stat.baseStats.hp = 45
    spewpa_stat.baseStats.attack = 22
    spewpa_stat.baseStats.defense = 60
    spewpa_stat.baseStats.speed = 29
    spewpa_stat.baseStats.specialAttack = 27
    spewpa_stat.baseStats.specialDefense = 30
    spewpa_stat.types.append("pokemon.type.bug")
    spewpa_stat.catchRate = 120
    spewpa_stat.evYield.defense = 2
    spewpa_stat.genderRatio = poke_math.PERCENT_FEMALE(50)
    spewpa_stat.hatchCycles = 15
    spewpa_stat.baseFriendship = 70
    spewpa_stat.growthRate = 0
    spewpa_stat.abilities.append("pokemon.ability.shed_skin")
    spewpa_stat.abilities.append("")
    spewpa_stat.abilities.append("pokemon.ability.friend_guard")

    vivillon_stat = pb_pokedex.Species()
    vivillon_stat.baseStats.hp = 80
    vivillon_stat.baseStats.attack = 52
    vivillon_stat.baseStats.defense = 50
    vivillon_stat.baseStats.speed = 89
    vivillon_stat.baseStats.specialAttack = 90
    vivillon_stat.baseStats.specialDefense = 50
    vivillon_stat.types.append("pokemon.type.bug")
    vivillon_stat.types.append("pokemon.type.flying")
    vivillon_stat.catchRate = 45
    vivillon_stat.evYield.hp = 1
    vivillon_stat.evYield.speed = 1
    vivillon_stat.evYield.specialAttack = 1
    vivillon_stat.genderRatio = poke_math.PERCENT_FEMALE(50)
    vivillon_stat.hatchCycles = 15
    vivillon_stat.baseFriendship = 70
    vivillon_stat.growthRate = 0
    vivillon_stat.abilities.append("pokemon.ability.shield_dust")
    vivillon_stat.abilities.append("pokemon.ability.compound_eyes")
    vivillon_stat.abilities.append("pokemon.ability.friend_guard")

    for form in [
        "ICY_SNOW", "POLAR", "TUNDRA", "CONTINENTAL", "GARDEN", "ELEGANT",
        "MEADOW", "MODERN", "MARINE", "ARCHIPELAGO", "HIGH_PLAINS",
        "SANDSTORM", "RIVER", "MONSOON", "SAVANNA", "SUN", "OCEAN",
        "JUNGLE", "FANCY", "POKEBALL"
    ]:
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(scatterbug_stat)
        _stats["SCATTERBUG_" + form] = form_stat
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(spewpa_stat)
        _stats["SPEWPA_" + form] = form_stat
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(vivillon_stat)
        _stats["VIVILLON_" + form] = form_stat

    flabebe_stat = pb_pokedex.Species()
    flabebe_stat.baseStats.hp = 44
    flabebe_stat.baseStats.attack = 38
    flabebe_stat.baseStats.defense = 39
    flabebe_stat.baseStats.speed = 42
    flabebe_stat.baseStats.specialAttack = 61
    flabebe_stat.baseStats.specialDefense = 79
    flabebe_stat.types.append("pokemon.type.fairy")
    flabebe_stat.catchRate = 255
    flabebe_stat.evYield.specialDefense = 1
    flabebe_stat.genderRatio = 254
    flabebe_stat.hatchCycles = 20
    flabebe_stat.baseFriendship = 70
    flabebe_stat.growthRate = 0
    flabebe_stat.abilities.append("pokemon.ability.natural_cure")
    flabebe_stat.abilities.append("")
    flabebe_stat.abilities.append("")

    floette_stat = pb_pokedex.Species()
    floette_stat.baseStats.hp = 54
    floette_stat.baseStats.attack = 45
    floette_stat.baseStats.defense = 47
    floette_stat.baseStats.speed = 52
    floette_stat.baseStats.specialAttack = 75
    floette_stat.baseStats.specialDefense = 98
    floette_stat.types.append("pokemon.type.fairy")
    floette_stat.catchRate = 120
    floette_stat.evYield.specialDefense = 2
    floette_stat.genderRatio = 254
    floette_stat.hatchCycles = 20
    floette_stat.baseFriendship = 70
    floette_stat.growthRate = 0
    floette_stat.abilities.append("pokemon.ability.natural_cure")
    floette_stat.abilities.append("")
    floette_stat.abilities.append("")

    florges_stat = pb_pokedex.Species()
    florges_stat.baseStats.hp = 78
    florges_stat.baseStats.attack = 65
    florges_stat.baseStats.defense = 68
    florges_stat.baseStats.speed = 75
    florges_stat.baseStats.specialAttack = 112
    florges_stat.baseStats.specialDefense = 154
    florges_stat.types.append("pokemon.type.fairy")
    florges_stat.catchRate = 45
    florges_stat.evYield.specialDefense = 3
    florges_stat.genderRatio = 254
    florges_stat.hatchCycles = 20
    florges_stat.baseFriendship = 70
    florges_stat.growthRate = 0
    florges_stat.abilities.append("pokemon.ability.natural_cure")
    florges_stat.abilities.append("")
    florges_stat.abilities.append("")

    for form in ["RED", "YELLOW", "ORANGE", "BLUE", "WHITE"]:
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(flabebe_stat)
        _stats["FLABEBE_" + form] = form_stat
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(floette_stat)
        _stats["FLOETTE_" + form] = form_stat
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(florges_stat)
        _stats["FLORGES_" + form] = form_stat

    floette_eternal_stat = pb_pokedex.Species()
    floette_eternal_stat.baseStats.hp = 74
    floette_eternal_stat.baseStats.attack = 65
    floette_eternal_stat.baseStats.defense = 67
    floette_eternal_stat.baseStats.speed = 92
    floette_eternal_stat.baseStats.specialAttack = 125
    floette_eternal_stat.baseStats.specialDefense = 128
    floette_eternal_stat.types.append("pokemon.type.fairy")
    floette_eternal_stat.catchRate = 120
    floette_eternal_stat.evYield.specialDefense = 2
    floette_eternal_stat.genderRatio = 254
    floette_eternal_stat.hatchCycles = 20
    floette_eternal_stat.baseFriendship = 70
    floette_eternal_stat.growthRate = 0
    floette_eternal_stat.abilities.append("pokemon.ability.natural_cure")
    floette_eternal_stat.abilities.append("")
    floette_eternal_stat.abilities.append("")

    _stats["FLOETTE_ETERNAL"] = floette_eternal_stat

    furfrou_stat = pb_pokedex.Species()
    furfrou_stat.baseStats.hp = 75
    furfrou_stat.baseStats.attack = 90
    furfrou_stat.baseStats.defense = 60
    furfrou_stat.baseStats.speed = 102
    furfrou_stat.baseStats.specialAttack = 65
    furfrou_stat.baseStats.specialDefense = 90
    furfrou_stat.types.append("pokemon.type.normal")
    furfrou_stat.catchRate = 160
    furfrou_stat.evYield.speed = 1
    furfrou_stat.genderRatio = poke_math.PERCENT_FEMALE(50)
    furfrou_stat.hatchCycles = 20
    furfrou_stat.baseFriendship = 70
    furfrou_stat.growthRate = 0
    furfrou_stat.abilities.append("pokemon.ability.fur_coat")
    furfrou_stat.abilities.append("")
    furfrou_stat.abilities.append("")

    for form in [
        "NATURAL", "HEART", "STAR", "DIAMOND", "DEBUTANTE", "MATRON",
        "DANDY", "LA_REINE", "KABUKI", "PHARAOH"
    ]:
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(furfrou_stat)
        _stats["FURFROU_" + form + (
            "" if form == "NATURAL" else "_TRIM")] = form_stat

    silvally_stat = pb_pokedex.Species()
    silvally_stat.baseStats.hp = 100
    silvally_stat.baseStats.attack = 100
    silvally_stat.baseStats.defense = 100
    silvally_stat.baseStats.speed = 100
    silvally_stat.baseStats.specialAttack = 100
    silvally_stat.baseStats.specialDefense = 100
    silvally_stat.catchRate = 3
    silvally_stat.evYield.hp = 3
    silvally_stat.genderRatio = 255
    silvally_stat.hatchCycles = 120
    silvally_stat.baseFriendship = 0
    silvally_stat.growthRate = 5
    silvally_stat.abilities.append("pokemon.ability.rks_system")
    silvally_stat.abilities.append("")
    silvally_stat.abilities.append("")

    for p_type in [
        "NORMAL", "FIGHTING", "FLYING", "POISON", "GROUND", "ROCK", "BUG",
        "GHOST", "STEEL", "FIRE", "WATER", "GRASS", "ELECTRIC", "PSYCHIC",
        "ICE", "DRAGON", "DARK", "FAIRY"
    ]:
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(silvally_stat)
        form_stat.types.append("pokemon.type." + p_type.lower())
        _stats["SILVALLY_" + p_type] = form_stat

    minior_m_stat = pb_pokedex.Species()
    minior_m_stat.baseStats.hp = 60
    minior_m_stat.baseStats.attack = 60
    minior_m_stat.baseStats.defense = 100
    minior_m_stat.baseStats.speed = 60
    minior_m_stat.baseStats.specialAttack = 60
    minior_m_stat.baseStats.specialDefense = 100
    minior_m_stat.types.append("pokemon.type.rock")
    minior_m_stat.types.append("pokemon.type.flying")
    minior_m_stat.catchRate = 30
    minior_m_stat.evYield.defense = 1
    minior_m_stat.evYield.specialDefense = 1
    minior_m_stat.genderRatio = 255
    minior_m_stat.hatchCycles = 25
    minior_m_stat.baseFriendship = 70
    minior_m_stat.growthRate = 3
    minior_m_stat.abilities.append("pokemon.ability.shields_down")
    minior_m_stat.abilities.append("")
    minior_m_stat.abilities.append("")

    minior_c_stat = pb_pokedex.Species()
    minior_c_stat.baseStats.hp = 60
    minior_c_stat.baseStats.attack = 100
    minior_c_stat.baseStats.defense = 60
    minior_c_stat.baseStats.speed = 120
    minior_c_stat.baseStats.specialAttack = 100
    minior_c_stat.baseStats.specialDefense = 60
    minior_c_stat.types.append("pokemon.type.rock")
    minior_c_stat.types.append("pokemon.type.flying")
    minior_c_stat.catchRate = 30
    minior_c_stat.evYield.defense = 1
    minior_c_stat.evYield.specialDefense = 1
    minior_c_stat.genderRatio = 255
    minior_c_stat.hatchCycles = 25
    minior_c_stat.baseFriendship = 70
    minior_c_stat.growthRate = 3
    minior_c_stat.abilities.append("pokemon.ability.shields_down")
    minior_c_stat.abilities.append("")
    minior_c_stat.abilities.append("")

    for form in [
        "RED", "ORANGE", "YELLOW", "GREEN", "BLUE", "INDIGO", "VIOLET"
    ]:
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(minior_m_stat)
        _stats["MINIOR_METEOR_" + form] = form_stat

        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(minior_c_stat)
        _stats["MINIOR_CORE_" + form] = form_stat

    alcremie_stat = pb_pokedex.Species()
    alcremie_stat.baseStats.hp = 65
    alcremie_stat.baseStats.attack = 60
    alcremie_stat.baseStats.defense = 75
    alcremie_stat.baseStats.speed = 64
    alcremie_stat.baseStats.specialAttack = 110
    alcremie_stat.baseStats.specialDefense = 121
    alcremie_stat.types.append("pokemon.type.fairy")
    alcremie_stat.catchRate = 100
    alcremie_stat.evYield.specialDefense = 1
    alcremie_stat.genderRatio = 254
    alcremie_stat.hatchCycles = 20
    alcremie_stat.baseFriendship = 70
    alcremie_stat.growthRate = 0
    alcremie_stat.abilities.append("pokemon.ability.sweet_veil")
    alcremie_stat.abilities.append("")
    alcremie_stat.abilities.append("pokemon.ability.aroma_veil")

    for form_sweet in [
        "STRAWBERRY", "BERRY", "LOVE", "STAR", "CLOVER", "FLOWER", "RIBBON"
    ]:
        for form_cream in [
            "VANILLA_CREAM", "RUBY_CREAM", "MATCHA_CREAM", "MINT_CREAM",
            "LEMON_CREAM", "SALTED_CREAM", "RUBY_SWIRL", "CARAMEL_SWIRL",
            "RAINBOW_SWIRL"
        ]:
            form_stat = pb_pokedex.Species()
            form_stat.CopyFrom(alcremie_stat)
            _stats[f"ALCREMIE_{form_sweet}_{form_cream}"] = form_stat

    form_stat = pb_pokedex.Species()
    form_stat.CopyFrom(alcremie_stat)
    _stats[f"ALCREMIE_GMAX"] = form_stat

    ogerpon_stat = pb_pokedex.Species()
    ogerpon_stat.baseStats.hp = 80
    ogerpon_stat.baseStats.attack = 120
    ogerpon_stat.baseStats.defense = 84
    ogerpon_stat.baseStats.speed = 110
    ogerpon_stat.baseStats.specialAttack = 60
    ogerpon_stat.baseStats.specialDefense = 96
    ogerpon_stat.types.append("pokemon.type.grass")
    ogerpon_stat.catchRate = 5
    ogerpon_stat.evYield.attack = 3
    ogerpon_stat.genderRatio = 254
    ogerpon_stat.hatchCycles = 10
    ogerpon_stat.baseFriendship = 70
    ogerpon_stat.growthRate = 5

    for tera in ["", "_TERA"]:
        for form in ["TEAL", "WELLSPRING", "HEARTHFLAME", "CORNERSTONE"]:
            form_stat = pb_pokedex.Species()
            form_stat.CopyFrom(ogerpon_stat)

            if form == "TEAL":
                form_stat.abilities.append(
                    f"pokemon.ability.{"embody_aspect_(teal)" if tera == "_TERA" else "defiant"}")
                form_stat.abilities.append("")
                form_stat.abilities.append(
                    f"pokemon.ability.{"embody_aspect_(teal)" if tera == "_TERA" else "defiant"}")
            elif form == "WELLSPRING":
                form_stat.types.append("pokemon.type.water")
                form_stat.abilities.append(
                    f"pokemon.ability.{"embody_aspect_(wellspring)" if tera == "_TERA" else "water_absorb"}")
                form_stat.abilities.append("")
                form_stat.abilities.append(
                    f"pokemon.ability.{"embody_aspect_(wellspring)" if tera == "_TERA" else "water_absorb"}")
            elif form == "HEARTHFLAME":
                form_stat.types.append("pokemon.type.fire")
                form_stat.abilities.append(
                    f"pokemon.ability.{"embody_aspect_(hearthflame)" if tera == "_TERA" else "mold_breaker"}")
                form_stat.abilities.append("")
                form_stat.abilities.append(
                    f"pokemon.ability.{"embody_aspect_(hearthflame)" if tera == "_TERA" else "mold_breaker"}")
            elif form == "CORNERSTONE":
                form_stat.types.append("pokemon.type.rock")
                form_stat.abilities.append(
                    f"pokemon.ability.{"embody_aspect_(cornerstone)" if tera == "_TERA" else "sturdy"}")
                form_stat.abilities.append("")
                form_stat.abilities.append(
                    f"pokemon.ability.{"embody_aspect_(cornerstone)" if tera == "_TERA" else "sturdy"}")

            _stats[f"OGERPON_{form}{tera}"] = form_stat


def process():
    print("Processing Pokedex")
    process_species_forms()
    process_national_dex_ids()
    process_species_stats()


def handle_evos(base_entry: pb_pokedex.Species, entry: pb_pokedex.Species,
                evos: list[list[str]]):
    for evo in evos:
        target: pb_pokedex.Species = _stats[evo[2]]
        evo_data = pb_pokedex.Evolution()
        evo_data.to = target.id
        evo_data.fromForm = 0 if not entry.HasField("form") else entry.form
        evo_data.toForm = 0 if not target.HasField("form") else target.form
        append = False

        conditions = evo_data.conditions

        for evo_entry in base_entry.evolutions:
            if evo_entry.to == target.id and evo_entry.toForm == target.form and evo_entry.fromForm == evo_data.fromForm:
                append = True
                conditions = evo_entry.conditions["pokemon.evolve.or"].nested
                break

        if evo[0] == "EVO_NONE":
            continue
        elif evo[0] == "EVO_LEVEL":
            if not evo[1].isdigit():
                print(f"\tERROR: Level is not a number. Value: {evo[1]}")
                exit(-1)
            conditions["pokemon.evolve.level"].number = int(evo[1])
        elif evo[0] == "EVO_LEVEL_DAY":
            level_up = conditions["pokemon.evolve.levelUp"].nested
            level_up["pokemon.evolve.time"].string = "timeOfDay.day"
        elif evo[0] == "EVO_LEVEL_NIGHT":
            level_up = conditions["pokemon.evolve.levelUp"].nested
            level_up["pokemon.evolve.time"].string = "timeOfDay.night"
        elif evo[0] == "EVO_ITEM":
            item = get_item_string(evo[1].removeprefix("ITEM_"))
            if item is None:
                print(f"\tERROR: Missing item string \"{evo[1]}\"")
                exit(-1)
            conditions["pokemon.evolve.useItem"].string = item
        elif evo[0] == "EVO_FRIENDSHIP":
            level_up = conditions["pokemon.evolve.levelUp"].nested
            level_up["pokemon.evolve.friendship"].string = "friendship.high"
        elif evo[0] == "EVO_MOVE":
            move = get_move_string(evo[1].removeprefix("MOVE_"))
            if move is None:
                print(f"\tERROR: Missing move string \"{evo[1]}\"")
                exit(-1)
            level_up = conditions["pokemon.evolve.levelUp"].nested
            level_up["pokemon.evolve.knowMove"].string = move
        elif evo[0] == "EVO_TRADE_ITEM":
            item = get_item_string(evo[1].removeprefix("ITEM_"))
            if item is None:
                print(f"\tERROR: Missing item string \"{evo[1]}\"")
                exit(-1)
            trade = conditions["pokemon.evolve.trade"].nested
            trade["pokemon.evolve.holdItem"].string = item
        elif evo[0] == "EVO_TRADE":
            _ = conditions["pokemon.evolve.trade"].nested
        elif evo[0] == "EVO_MAPSEC":
            location = evo[1].removeprefix("MAPSEC_")

            if location == "NEW_MAUVILLE":
                location = "pokemon.location.gen3.new_mauville"
            else:
                print(f"\tERROR: Unknown location \"{location}\"")
                exit(-1)

            level_up = conditions["pokemon.evolve.levelUp"].nested
            level_up["pokemon.evolve.location"].string = location
        elif evo[0] == "EVO_FRIENDSHIP_DAY":
            level_up = conditions["pokemon.evolve.levelUp"].nested
            level_up["pokemon.evolve.time"].string = "timeOfDay.day"
            level_up["pokemon.evolve.friendship"].string = "friendship.high"
        elif evo[0] == "EVO_FRIENDSHIP_NIGHT":
            level_up = conditions["pokemon.evolve.levelUp"].nested
            level_up["pokemon.evolve.time"].string = "timeOfDay.night"
            level_up["pokemon.evolve.friendship"].string = "friendship.high"
        elif evo[0] == "EVO_FRIENDSHIP_MOVE_TYPE":
            level_up = conditions["pokemon.evolve.levelUp"].nested
            level_up[
                "pokemon.evolve.knowMoveType"].string = f"pokemon.type.{evo[1].removeprefix("TYPE_").lower()}"
            level_up["pokemon.evolve.friendship"].string = "friendship.high"
        elif evo[0] == "EVO_MOVE_TWO_SEGMENT":
            move = get_move_string(evo[1].removeprefix("MOVE_"))
            if move is None:
                print(f"\tERROR: Missing move string \"{evo[1]}\"")
                exit(-1)
            level_up = conditions["pokemon.evolve.levelUp"].nested
            level_up["pokemon.evolve.knowMove"].string = move
            level_up[
                "pokemon.evolve.rarity"].string = "rarity.randomPersonality"
        elif evo[0] == "EVO_LEVEL_ATK_LT_DEF" or evo[
            0] == "EVO_LEVEL_ATK_GT_DEF" or evo[0] == "EVO_LEVEL_ATK_EQ_DEF":
            evo_type = "stat.attack" + (
                "<" if evo[0] == "EVO_LEVEL_ATK_LT_DEF" else ">" if evo[
                                                                        0] == "EVO_LEVEL_ATK_GT_DEF" else "=") + "defense"
            conditions["pokemon.evolve.level"].number = int(evo[1])
            conditions["pokemon.evolve.stat"].string = evo_type
        elif evo[0] == "EVO_LEVEL_SILCOON" or evo[0] == "EVO_LEVEL_CASCOON":
            conditions["pokemon.evolve.level"].number = int(evo[1])
            conditions[
                "pokemon.evolve.rarity"].string = "rarity.randomPersonality"
        elif evo[0] == "EVO_ITEM_MALE":
            item = get_item_string(evo[1].removeprefix("ITEM_"))
            if item is None:
                print(f"\tERROR: Missing item string \"{evo[1]}\"")
                exit(-1)
            conditions["pokemon.evolve.useItem"].string = item
            conditions["pokemon.evolve.gender"].string = "Gender.male"
        elif evo[0] == "EVO_ITEM_FEMALE":
            item = get_item_string(evo[1].removeprefix("ITEM_"))
            if item is None:
                print(f"\tERROR: Missing item string \"{evo[1]}\"")
                exit(-1)
            conditions["pokemon.evolve.useItem"].string = item
            conditions["pokemon.evolve.gender"].string = "Gender.female"
        elif evo[0] == "EVO_LEVEL_NINJASK":
            if not evo[1].isdigit():
                print(f"\tERROR: Level is not a number. Value: {evo[1]}")
                exit(-1)
            shedinja = pb_pokedex.Evolution()
            shedinja.to = target.id + 1
            shedinja.fromForm = 0
            shedinja.toForm = 0

            shedinja.conditions["pokemon.evolve.level"].number = int(evo[1])
            shedinja.conditions["pokemon.evolve.emptySlot"].nested[
                "pokemon.evolve.hasItem"].string = "pokemon.ball.poke_ball"
            base_entry.evolutions.append(shedinja)
            conditions["pokemon.evolve.level"].number = int(evo[1])
        elif evo[0] == "EVO_BEAUTY":
            conditions["pokemon.evolve.levelUp"].nested[
                "pokemon.evolve.maxTrait"].string = "trait.beauty"
        elif evo[0] == "EVO_LEVEL_FEMALE":
            if not evo[1].isdigit():
                print(f"\tERROR: Level is not a number. Value: {evo[1]}")
                exit(-1)
            conditions["pokemon.evolve.level"].number = int(evo[1])
            conditions["pokemon.evolve.gender"].string = "Gender.female"
        elif evo[0] == "EVO_LEVEL_MALE":
            if not evo[1].isdigit():
                print(f"\tERROR: Level is not a number. Value: {evo[1]}")
                exit(-1)
            conditions["pokemon.evolve.level"].number = int(evo[1])
            conditions["pokemon.evolve.gender"].string = "Gender.male"
        elif evo[0] == "EVO_TRADE_SPECIFIC_MON":
            target_mon = _stats[evo[1].removeprefix("SPECIES_")]

            conditions["pokemon.evolve.trade"].nested[
                "pokemon.evolve.tradeWith"].string = target_mon.name
        elif evo[0] == "EVO_LEVEL_DARK_TYPE_MON_IN_PARTY":
            if not evo[1].isdigit():
                print(f"\tERROR: Level is not a number. Value: {evo[1]}")
                exit(-1)
            conditions["pokemon.evolve.level"].number = int(evo[1])
            conditions[
                "pokemon.evolve.typedPokemonPresentInParty"].string = "pokemon.type.dark"
        elif evo[0] == "EVO_LEVEL_RAIN":
            if not evo[1].isdigit():
                print(f"\tERROR: Level is not a number. Value: {evo[1]}")
                exit(-1)

            conditions["pokemon.evolve.level"].number = int(evo[1])
            conditions["pokemon.evolve.weather"].string = "weather.raining"
        elif evo[0] == "EVO_LEVEL_FOG":
            if not evo[1].isdigit():
                print(f"\tERROR: Level is not a number. Value: {evo[1]}")
                exit(-1)

            conditions["pokemon.evolve.level"].number = int(evo[1])
            conditions[
                "pokemon.evolve.weather"].string = "EmeraldImperium.Weather.fog"
        elif evo[0] == "EVO_LEVEL_DUSK":
            if not evo[1].isdigit():
                print(f"\tERROR: Level is not a number. Value: {evo[1]}")
                exit(-1)
            conditions["pokemon.evolve.level"].number = int(evo[1])
            conditions["pokemon.evolve.time"].string = "timeOfDay.dusk"
        elif evo[0] == "EVO_LEVEL_NATURE_AMPED":
            if not evo[1].isdigit():
                print(f"\tERROR: Level is not a number. Value: {evo[1]}")
                exit(-1)
            conditions["pokemon.evolve.level"].number = int(evo[1])
            conditions["pokemon.evolve.nature"].stringArray.extend([
                "pokemon.nature.brave",
                "pokemon.nature.adamant",
                "pokemon.nature.naughty",
                "pokemon.nature.docile",
                "pokemon.nature.impish",
                "pokemon.nature.lax",
                "pokemon.nature.hasty",
                "pokemon.nature.jolly",
                "pokemon.nature.naive",
                "pokemon.nature.rash",
                "pokemon.nature.sassy",
                "pokemon.nature.quirky"
            ])
        elif evo[0] == "EVO_LEVEL_NATURE_LOW_KEY":
            if not evo[1].isdigit():
                print(f"\tERROR: Level is not a number. Value: {evo[1]}")
                exit(-1)
            conditions["pokemon.evolve.level"].number = int(evo[1])
            conditions["pokemon.evolve.nature"].stringArray.extend([
                "pokemon.nature.lonely",
                "pokemon.nature.bold",
                "pokemon.nature.relaxed",
                "pokemon.nature.timid",
                "pokemon.nature.serious",
                "pokemon.nature.modest",
                "pokemon.nature.mild",
                "pokemon.nature.quiet",
                "pokemon.nature.bashful",
                "pokemon.nature.calm",
                "pokemon.nature.gentle",
                "pokemon.nature.careful"
            ])
        elif evo[0] == "EVO_LEVEL_FAMILY_OF_FOUR" or evo[
            0] == "EVO_LEVEL_FAMILY_OF_THREE":
            if not evo[1].isdigit():
                print(f"\tERROR: Level is not a number. Value: {evo[1]}")
                exit(-1)
            conditions["pokemon.evolve.level"].number = int(evo[1])
            if evo[0] == "EVO_LEVEL_FAMILY_OF_FOUR":
                conditions["pokemon.evolve.rarity"].string = "rarity.rare"
        else:
            print(f"\tERROR: Missing evo type \"{evo[0]}\"")
            exit(-1)

        if not append:
            base_entry.evolutions.append(evo_data)


def generate():
    translations.add_translation("EmeraldImperium.Weather.fog", "Fog")
    print("Generating Pokedex")

    sprite_dir = directories.get_output_dir("emerald_imperium/assets/pokemon")

    for dexId in collections.OrderedDict(sorted(_dex_ids.items())):
        game_id = _dex_ids[dexId]
        species = game_id
        species_id = game_id

        forms = _species_forms[species]
        first_form_key = next(iter(_species_forms[species]))
        first_form: pb_pokedex.Species = _stats[
            f"{species_id}{("" if first_form_key == "_" else f"_{first_form_key}")}"]
        first_form_key = None if first_form_key == "_" else first_form_key

        for form in forms:
            form = None if form == "_" else form
            form_id = form

            stat_id = f"{species_id}{("" if form is None else f"_{form}")}"

            if not _stats.__contains__(stat_id):
                print(f"\tWARNING: Missing stats for {stat_id}")
                continue

            stats: pb_pokedex.Species = _stats[stat_id]

            if form is not None:
                if form == "NORMAL":
                    form = None
                elif form == "M" and stats.genderRatio != 254 and stats.genderRatio != 255:
                    form = "MALE"
                elif form == "F" and stats.genderRatio != 0 and stats.genderRatio != 255:
                    form = "FEMALE"
                elif form == "RED_STRIPED":
                    form = "RED"
                elif form == "BLUE_STRIPED":
                    form = "BLUE"
                elif form == "WHITE_STRIPED":
                    form = "WHITE"
                elif form == "THREE" or form == "FOUR":
                    form = "FAMILY_OF_" + form
                elif form == "AMPED":
                    form = "AMPED_FORM"
                elif form == "50":
                    form = "50%"
                elif form.startswith("METEOR"):
                    form = form.replace("METEOR", "M")
                elif form.startswith("CORE"):
                    form = form.replace("CORE", "C")
                elif form.endswith("TRIM"):
                    form = form.replace("_TRIM", "")
                elif form == "TOTEM":
                    form = "LARGE"
                elif form == "ALOLA_TOTEM":
                    form = "LARGE"
                elif form == "TOTEM_DISGUISED":
                    form = "LARGE"
                elif form == "BUSTED_TOTEM":
                    form = "LARGE_BUSTED"
                elif form == "10_AURA_BREAK" or form == "10_POWER_CONSTRUCT" or form == "50_POWER_CONSTRUCT":
                    form = form[:2] + "%"
                elif form == "NOICE":
                    form = "NOICE_FACE"
                elif form == "GALAR_STANDARD":
                    form = "GALAR"
                elif species == "TAUROS":
                    form = form.removeprefix("PALDEA_")
                elif form == "SPIKY_EARED":
                    form = "SPIKY"
                elif form == "GMAX":
                    form = "GIGANTAMAX"
                elif form == "STARTER":
                    form = "PARTNER"
                elif form == "POKEBALL":
                    form = "POKé_BALL".upper()
                elif form == "DUSK_MANE":
                    form = "DUSK"
                elif form == "DAWN_WINGS":
                    form = "DAWN"
                elif species == "KELDEO" and form == "ORDINARY":
                    form = None
                elif species == "DARMANITAN":
                    if form == "STANDARD":
                        form = None
                elif species == "EISCUE" and form == "ICE":
                    form = None
                elif form == "HERO":
                    form = None
            else:
                if species == "UNOWN":
                    form = "A"

            stats.id = dexId

            file_form_id = f"{game_strings.clean_up(species_id)}{"" if form_id is None else f"-{game_strings.clean_up(form_id)}"}"
            file_id = f"{game_strings.clean_up(species_id)}"

            if os.path.isfile(
                    os.path.join(sprite_dir, "party", f"{file_form_id}.gif")):
                stats.sprites.party = f"pokelink-community:/emerald_imperium/assets/pokemon/party/{file_form_id}.gif"
            elif os.path.isfile(os.path.join(sprite_dir, "shiny",
                                             f"{file_id}-gmax.gif")) and species != "EEVEE":
                stats.sprites.normal = f"pokelink-community:/emerald_imperium/assets/pokemon/party/{file_id}-gmax.gif"
            elif os.path.isfile(
                    os.path.join(sprite_dir, "party", f"{file_id}.gif")):
                stats.sprites.party = f"pokelink-community:/emerald_imperium/assets/pokemon/party/{file_id}.gif"
            else:
                print(
                    f"\tWARNING: Not able to find a party sprite for {file_form_id}")

            if os.path.isfile(
                    os.path.join(sprite_dir, "normal", f"{file_form_id}.png")):
                stats.sprites.normal = f"pokelink-community:/emerald_imperium/assets/pokemon/normal/{file_form_id}.png"
            elif os.path.isfile(os.path.join(sprite_dir, "normal",
                                             f"{file_id}-gmax.png")) and species != "EEVEE":
                stats.sprites.normal = f"pokelink-community:/emerald_imperium/assets/pokemon/normal/{file_id}-gmax.png"
            elif os.path.isfile(
                    os.path.join(sprite_dir, "normal", f"{file_id}.png")):
                stats.sprites.normal = f"pokelink-community:/emerald_imperium/assets/pokemon/normal/{file_id}.png"
            else:
                print(
                    f"\tWARNING: Not able to find a normal sprite for {file_form_id}")

            if os.path.isfile(
                    os.path.join(sprite_dir, "shiny", f"{file_form_id}.png")):
                stats.sprites.shiny = f"pokelink-community:/emerald_imperium/assets/pokemon/shiny/{file_form_id}.png"
            elif os.path.isfile(os.path.join(sprite_dir, "shiny",
                                             f"{file_id}-gmax.png")) and species != "EEVEE":
                stats.sprites.shiny = f"pokelink-community:/emerald_imperium/assets/pokemon/shiny/{file_id}-gmax.png"
            elif os.path.isfile(
                    os.path.join(sprite_dir, "shiny", f"{file_id}.png")):
                stats.sprites.shiny = f"pokelink-community:/emerald_imperium/assets/pokemon/shiny/{file_id}.png"
            else:
                print(
                    f"\tWARNING: Not able to find a shiny sprite for {file_form_id}")

            if os.path.isfile(os.path.join(sprite_dir, "normal",
                                           f"{file_form_id}-f.png")) and stats.genderRatio != 0 and stats.genderRatio != 255:
                stats.sprites.female = f"pokelink-community:/emerald_imperium/assets/pokemon/normal/{file_form_id}-f.png"

            if os.path.isfile(os.path.join(sprite_dir, "shiny",
                                           f"{file_form_id}-f.png")) and stats.genderRatio != 0 and stats.genderRatio != 255:
                stats.sprites.femaleShiny = f"pokelink-community:/emerald_imperium/assets/pokemon/shiny/{file_form_id}-f.png"

            stats.name = f"pokemon.species.{game_strings.clean_up(species)}"

            stats.gameId = _species_form_id[stat_id]

            if form is not None:
                if game_strings.has_form(form):
                    stats.formName = "pokemon.form." + game_strings.clean_up(
                        form)
                else:
                    split = form.split("_")
                    first = True
                    form_translation = ""
                    for f in split:
                        if first:
                            first = False
                            form_translation = f[0] + f[1:].lower()
                            continue

                        form_translation += " " + f[0] + f[1:].lower()

                    translations.add_translation(
                        f"EmeraldImperium.Form.{game_strings.clean_up(form_translation)}",
                        form_translation)
                    stats.formName = f"EmeraldImperium.Form.{game_strings.clean_up(form_translation)}"

            if first_form_key != form_id:
                stats.form = forms[form_id]
                first_form.forms.append(stats)

    for dexId in collections.OrderedDict(sorted(_dex_ids.items())):
        game_id = _dex_ids[dexId]
        species = game_id
        species_id = game_id

        forms = _species_forms[species]
        first_form_key = next(iter(_species_forms[species]))
        first_form: pb_pokedex.Species = _stats[
            f"{species_id}{("" if first_form_key == "_" else f"_{first_form_key}")}"]

        for form in forms:
            form = None if form == "_" else form

            stat_id = f"{species_id}{("" if form is None else f"_{form}")}"

            if not _stats.__contains__(stat_id):
                continue

            stats: pb_pokedex.Species = _stats[stat_id]

            if _evolutions.__contains__(stat_id):
                handle_evos(first_form, stats, _evolutions[stat_id])

    for dexId in collections.OrderedDict(sorted(_dex_ids.items())):
        game_id = _dex_ids[dexId]
        species = game_id
        species_id = game_id

        first_form_key = next(iter(_species_forms[species]))
        first_form: pb_pokedex.Species = _stats[
            f"{species_id}{("" if first_form_key == "_" else f"_{first_form_key}")}"]

        for form in first_form.forms:
            form.ClearField("id")

        _dex.entries.append(first_form)

    write_file(
        os.path.join(directories.get_output_dir("emerald_imperium", True),
                     "emeraldImperium.dex"), json_format.MessageToDict(_dex))
