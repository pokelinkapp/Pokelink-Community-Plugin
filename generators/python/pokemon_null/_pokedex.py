import collections

import pokelink.proto.v0_7_1.pokedex_pb2 as pb_pokedex
import pokelink.directories as directories
import pokelink.translations as translations
from google.protobuf import json_format

from pokemon_null._items import get_item_string
from pokemon_null._moves import get_move_string
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
    with (open(os.path.join(directories.get_external_dir("private"), "pokemon_null",
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
            
            if (items[-3] == "FORMS_START"):
                internal_id += _species_form_id["PECHARUNT"]

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
    with open(os.path.join(directories.get_external_dir("private"), "pokemon_null",
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
    return int(line.removesuffix("\\").rstrip().removesuffix(",").split(" ")[-1])


def process_species_stats():
    global _stats
    print("\tProcessing Stats")

    lines = []

    for info in [
        "species_info.h"
    ]:
        with open(os.path.join(directories.get_external_dir("private"), "pokemon_null",
                               "src", "data", "pokemon", info), "r") as file:
            lines += [strip_comments(line) for line in file]

    reading = False
    reading_evolutions = False
    current_evos = []
    current_pokemon: pb_pokedex.Species | None = None
    current_name: str | None = None

    for line in lines:
        line = line.removesuffix("\\").strip()
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
                if current_pokemon.types.__len__() == 0:
                    types = line.removeprefix(".types = { ").removesuffix(
                        "},").split(", ")
    
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
            if line.endswith("] =") or line.endswith("]  =") or line.endswith("]   ="):
                current_name = line.removeprefix("[SPECIES_").removesuffix(
                    "] =").removesuffix("]   =").removesuffix("]  =")
                current_pokemon = pb_pokedex.Species()
                reading = True
            continue

    unown_stat = pb_pokedex.Species()
    unown_stat.baseStats.hp = 48
    unown_stat.baseStats.attack = 72
    unown_stat.baseStats.defense = 48
    unown_stat.baseStats.speed = 48
    unown_stat.baseStats.specialAttack = 72
    unown_stat.baseStats.specialDefense = 48
    unown_stat.types.append("pokemon.type.psychic")
    unown_stat.catchRate = 200
    unown_stat.evYield.attack = 1
    unown_stat.evYield.specialAttack = 1
    unown_stat.genderRatio = 255
    unown_stat.hatchCycles = 40
    unown_stat.baseFriendship = 70
    unown_stat.growthRate = _growth_indexes["GROWTH_MEDIUM_FAST"]
    unown_stat.abilities.append("pokemon.ability.levitate")
    unown_stat.abilities.append("")

    _stats["UNOWN"] = unown_stat

    for form in "B|C|D|E|F|G|H|I|J|K|L|M|N|O|P|Q|R|S|T|U|V|W|X|Y|Z".split(
            "|") + [
                    "EMARK", "QMARK"
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

    for form in ["DOUSE_DRIVE", "SHOCK_DRIVE", "BURN_DRIVE", "CHILL_DRIVE"]:
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
        "JUNGLE", "FANCY", "POKE_BALL"
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

    for form in ["", "_RED_FLOWER", "_YELLOW_FLOWER", "_ORANGE_FLOWER", "_BLUE_FLOWER", "_WHITE_FLOWER"]:
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(flabebe_stat)
        _stats["FLABEBE" + form] = form_stat
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(floette_stat)
        _stats["FLOETTE" + form] = form_stat
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(florges_stat)
        _stats["FLORGES" + form] = form_stat

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
    
    _stats["SILVALLY"] = silvally_stat

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
    
    _stats["MINIOR"] = minior_m_stat

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

    for form_cream in [
        "VANILLA_CREAM", "RUBY_CREAM", "MATCHA_CREAM", "MINT_CREAM",
        "LEMON_CREAM", "SALTED_CREAM", "RUBY_SWIRL", "CARAMEL_SWIRL",
        "RAINBOW_SWIRL"
    ]:
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(alcremie_stat)
        _stats[f"ALCREMIE_{form_cream}"] = form_stat

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
    
    _stats["OGERPON"] = ogerpon_stat

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
                
                _stats["OGERPON_TERA"] = form_stat
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

            _stats[f"OGERPON_{form}_MASK{tera}"] = form_stat
            
    pikachu_stat = pb_pokedex.Species()
    pikachu_stat.baseStats.hp = 35
    pikachu_stat.baseStats.attack = 55
    pikachu_stat.baseStats.speed = 90
    pikachu_stat.baseStats.specialAttack = 50
    pikachu_stat.baseStats.defense = 40
    pikachu_stat.baseStats.specialDefense = 50
    pikachu_stat.types.append("pokemon.type.electric")
    pikachu_stat.catchRate = 200
    pikachu_stat.evYield.speed = 2
    pikachu_stat.hatchCycles = 10
    pikachu_stat.genderRatio = poke_math.PERCENT_FEMALE(50)
    pikachu_stat.baseFriendship = 70
    pikachu_stat.abilities.append("pokemon.ability.volt_absorb")
    pikachu_stat.abilities.append("")
    pikachu_stat.abilities.append("pokemon.ability.static")
    pikachu_stat.growthRate = 0
    
    _stats["PIKACHU"] = pikachu_stat
    _stats["PIKACHU_ORIGINAL_CAP"] = pikachu_stat.__deepcopy__()
    _stats["PIKACHU_HOENN_CAP"] = pikachu_stat.__deepcopy__()
    _stats["PIKACHU_SINNOH_CAP"] = pikachu_stat.__deepcopy__().__deepcopy__()
    _stats["PIKACHU_UNOVA_CAP"] = pikachu_stat.__deepcopy__()
    _stats["PIKACHU_KALOS_CAP"] = pikachu_stat.__deepcopy__()
    _stats["PIKACHU_WORLD_CAP"] = pikachu_stat.__deepcopy__()
    _stats["PIKACHU_ALOLA_CAP"] = pikachu_stat.__deepcopy__()
    
    pikachu_cosplay = pb_pokedex.Species()
    pikachu_cosplay.CopyFrom(pikachu_stat)
    
    pikachu_cosplay.genderRatio = 254
    
    _stats["PIKACHU_COSPLAY"] = pikachu_cosplay
    _stats["PIKACHU_ROCK_STAR"] = pikachu_cosplay
    _stats["PIKACHU_BELLE"] = pikachu_cosplay
    _stats["PIKACHU_POP_STAR"] = pikachu_cosplay
    _stats["PIKACHU_PH_D"] = pikachu_cosplay
    _stats["PIKACHU_LIBRE"] = pikachu_cosplay

    pichu_stat = pb_pokedex.Species()
    pichu_stat.baseStats.hp = 48
    pichu_stat.baseStats.attack = 72
    pichu_stat.baseStats.speed = 48
    pichu_stat.baseStats.specialAttack = 72
    pichu_stat.baseStats.defense = 48
    pichu_stat.baseStats.specialDefense = 48
    pichu_stat.types.append("pokemon.type.electric")
    pichu_stat.catchRate = 200
    pichu_stat.evYield.attack = 1
    pichu_stat.evYield.specialAttack = 1
    pichu_stat.hatchCycles = 40
    pichu_stat.genderRatio = poke_math.PERCENT_FEMALE(50)
    pichu_stat.baseFriendship = 70
    pichu_stat.abilities.append("pokemon.ability.volt_absorb")
    pichu_stat.abilities.append("")
    pichu_stat.abilities.append("pokemon.ability.lightning_rod")
    pichu_stat.growthRate = 0

    _stats["PICHU"] = pichu_stat
    _stats["PICHU_SPIKY_EARED"] = pichu_stat.__deepcopy__()

    castform_stat = pb_pokedex.Species()
    castform_stat.baseStats.hp = 70
    castform_stat.baseStats.attack = 70
    castform_stat.baseStats.speed = 70
    castform_stat.baseStats.specialAttack = 70
    castform_stat.baseStats.defense = 70
    castform_stat.baseStats.specialDefense = 70
    castform_stat.types.append("pokemon.type.normal")
    castform_stat.catchRate = 15
    castform_stat.evYield.hp = 1
    castform_stat.hatchCycles = 25
    castform_stat.genderRatio = poke_math.PERCENT_FEMALE(50)
    castform_stat.baseFriendship = 70
    castform_stat.abilities.append("pokemon.ability.forecast")
    castform_stat.abilities.append("")
    castform_stat.growthRate = _growth_indexes["GROWTH_MEDIUM_FAST"]

    _stats["CASTFORM"] = castform_stat
    
    castform_sunny = pb_pokedex.Species()
    castform_sunny.CopyFrom(castform_stat)
    castform_sunny.types.clear()
    castform_sunny.types.append("pokemon.type.fire")
    
    _stats["CASTFORM_SUNNY"] = castform_sunny

    castform_rainy = pb_pokedex.Species()
    castform_rainy.CopyFrom(castform_stat)
    castform_rainy.types.clear()
    castform_rainy.types.append("pokemon.type.water")

    _stats["CASTFORM_RAINY"] = castform_rainy

    castform_snowy = pb_pokedex.Species()
    castform_snowy.CopyFrom(castform_stat)
    castform_snowy.types.clear()
    castform_snowy.types.append("pokemon.type.ice")

    _stats["CASTFORM_SNOWY"] = castform_snowy

    burmy_stat = pb_pokedex.Species()
    burmy_stat.baseStats.hp = 40
    burmy_stat.baseStats.attack = 29
    burmy_stat.baseStats.defense = 45
    burmy_stat.baseStats.speed = 36
    burmy_stat.baseStats.specialAttack = 29
    burmy_stat.baseStats.specialDefense = 45
    burmy_stat.types.append("pokemon.type.bug")
    burmy_stat.catchRate = 200
    burmy_stat.evYield.specialDefense = 1
    burmy_stat.genderRatio = poke_math.PERCENT_FEMALE(50)
    burmy_stat.hatchCycles = 15
    burmy_stat.baseFriendship = 70
    burmy_stat.abilities.append("pokemon.ability.shed_skin")
    burmy_stat.abilities.append("")
    burmy_stat.abilities.append("pokemon.ability.overcoat")
    burmy_stat.growthRate = 0

    burmy_grass = pb_pokedex.Species()
    burmy_grass.CopyFrom(burmy_stat)
    burmy_grass.types.append("pokemon.type.grass")
    _stats["BURMY"] = burmy_grass
    burmy_sand = pb_pokedex.Species()
    burmy_sand.CopyFrom(burmy_stat)
    burmy_sand.types.append("pokemon.type.ground")
    _stats["BURMY_SANDY_CLOAK"] = burmy_sand
    burmy_trash = pb_pokedex.Species()
    burmy_trash.CopyFrom(burmy_stat)
    burmy_trash.types.append("pokemon.type.steel")
    _stats["BURMY_TRASH_CLOAK"] = burmy_trash

    cherrim_stat = pb_pokedex.Species()
    cherrim_stat.baseStats.hp = 70
    cherrim_stat.baseStats.attack = 60
    cherrim_stat.baseStats.defense = 70
    cherrim_stat.baseStats.speed = 85
    cherrim_stat.baseStats.specialAttack = 87
    cherrim_stat.baseStats.specialDefense = 78
    cherrim_stat.types.append("pokemon.type.grass")
    cherrim_stat.catchRate = 200
    cherrim_stat.evYield.specialAttack = 1
    cherrim_stat.genderRatio = poke_math.PERCENT_FEMALE(50)
    cherrim_stat.hatchCycles = 20
    cherrim_stat.baseFriendship = 70
    cherrim_stat.abilities.append("pokemon.ability.flower_gift")
    cherrim_stat.abilities.append("")
    cherrim_stat.growthRate = 0

    _stats["CHERRIM"] = cherrim_stat
    _stats["CHERRIM_SUNSHINE"] = cherrim_stat.__deepcopy__()

    shellos_stat = pb_pokedex.Species()
    shellos_stat.baseStats.hp = 76
    shellos_stat.baseStats.attack = 48
    shellos_stat.baseStats.defense = 48
    shellos_stat.baseStats.speed = 34
    shellos_stat.baseStats.specialAttack = 57
    shellos_stat.baseStats.specialDefense = 62
    shellos_stat.types.append("pokemon.type.water")
    shellos_stat.catchRate = 200
    shellos_stat.evYield.hp = 1
    shellos_stat.genderRatio = poke_math.PERCENT_FEMALE(50)
    shellos_stat.hatchCycles = 20
    shellos_stat.baseFriendship = 70
    shellos_stat.abilities.append("pokemon.ability.rain_dish")
    shellos_stat.abilities.append("pokemon.ability.sand_force")
    shellos_stat.abilities.append("pokemon.ability.storm_drain")
    shellos_stat.growthRate = 0

    _stats["SHELLOS"] = shellos_stat
    _stats["SHELLOS_EAST_SEA"] = shellos_stat.__deepcopy__()

    gastrodon_stats = pb_pokedex.Species()
    gastrodon_stats.baseStats.hp = 111
    gastrodon_stats.baseStats.attack = 83
    gastrodon_stats.baseStats.defense = 68
    gastrodon_stats.baseStats.speed = 39
    gastrodon_stats.baseStats.specialAttack = 92
    gastrodon_stats.baseStats.specialDefense = 82
    gastrodon_stats.types.append("pokemon.type.water")
    gastrodon_stats.types.append("pokemon.type.ground")
    gastrodon_stats.catchRate = 200
    gastrodon_stats.evYield.hp = 2
    gastrodon_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    gastrodon_stats.hatchCycles = 20
    gastrodon_stats.baseFriendship = 70
    gastrodon_stats.abilities.append("pokemon.ability.rain_dish")
    gastrodon_stats.abilities.append("pokemon.ability.sand_force")
    gastrodon_stats.abilities.append("pokemon.ability.storm_drain")
    gastrodon_stats.growthRate = 0

    _stats["GASTRODON"] = gastrodon_stats
    _stats["GASTRODON_EAST_SEA"] = gastrodon_stats.__deepcopy__()

    deerling_stats = pb_pokedex.Species()
    deerling_stats.baseStats.hp = 60
    deerling_stats.baseStats.attack = 60
    deerling_stats.baseStats.defense = 50
    deerling_stats.baseStats.speed = 75
    deerling_stats.baseStats.specialAttack = 40
    deerling_stats.baseStats.specialDefense = 50
    deerling_stats.types.append("pokemon.type.normal")
    deerling_stats.types.append("pokemon.type.grass")
    deerling_stats.catchRate = 200
    deerling_stats.evYield.speed = 1
    deerling_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    deerling_stats.hatchCycles = 20
    deerling_stats.baseFriendship = 70
    deerling_stats.abilities.append("pokemon.ability.chlorophyll")
    deerling_stats.abilities.append("pokemon.ability.sap_sipper")
    deerling_stats.abilities.append("pokemon.ability.serene_grace")
    deerling_stats.growthRate = 0

    _stats["DEERLING"] = deerling_stats
    _stats["DEERLING_SUMMER"] = deerling_stats.__deepcopy__()
    _stats["DEERLING_AUTUMN"] = deerling_stats.__deepcopy__()
    _stats["DEERLING_WINTER"] = deerling_stats.__deepcopy__()

    sawsbuck_stats = pb_pokedex.Species()
    sawsbuck_stats.baseStats.hp = 80
    sawsbuck_stats.baseStats.attack = 100
    sawsbuck_stats.baseStats.defense = 70
    sawsbuck_stats.baseStats.speed = 95
    sawsbuck_stats.baseStats.specialAttack = 60
    sawsbuck_stats.baseStats.specialDefense = 70
    sawsbuck_stats.types.append("pokemon.type.normal")
    sawsbuck_stats.types.append("pokemon.type.grass")
    sawsbuck_stats.catchRate = 200
    sawsbuck_stats.evYield.attack = 2
    sawsbuck_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    sawsbuck_stats.hatchCycles = 20
    sawsbuck_stats.baseFriendship = 70
    sawsbuck_stats.abilities.append("pokemon.ability.chlorophyll")
    sawsbuck_stats.abilities.append("pokemon.ability.sap_sipper")
    sawsbuck_stats.abilities.append("pokemon.ability.serene_grace")
    sawsbuck_stats.growthRate = 0

    _stats["SAWSBUCK"] = sawsbuck_stats
    _stats["SAWSBUCK_SUMMER"] = sawsbuck_stats.__deepcopy__()
    _stats["SAWSBUCK_AUTUMN"] = sawsbuck_stats.__deepcopy__()
    _stats["SAWSBUCK_WINTER"] = sawsbuck_stats.__deepcopy__()

    furfrou_stats = pb_pokedex.Species()
    furfrou_stats.baseStats.hp = 75
    furfrou_stats.baseStats.attack = 80
    furfrou_stats.baseStats.defense = 60
    furfrou_stats.baseStats.speed = 102
    furfrou_stats.baseStats.specialAttack = 65
    furfrou_stats.baseStats.specialDefense = 90
    furfrou_stats.types.append("pokemon.type.normal")
    furfrou_stats.catchRate = 200
    furfrou_stats.evYield.speed = 1
    furfrou_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    furfrou_stats.hatchCycles = 20
    furfrou_stats.baseFriendship = 70
    furfrou_stats.abilities.append("pokemon.ability.fur_coat")
    furfrou_stats.abilities.append("")
    furfrou_stats.growthRate = 0

    _stats["FURFROU"] = furfrou_stats

    xerneas_stats = pb_pokedex.Species()
    xerneas_stats.baseStats.hp = 126
    xerneas_stats.baseStats.attack = 131
    xerneas_stats.baseStats.defense = 95
    xerneas_stats.baseStats.speed = 99
    xerneas_stats.baseStats.specialAttack = 131
    xerneas_stats.baseStats.specialDefense = 98
    xerneas_stats.types.append("pokemon.type.fairy")
    xerneas_stats.catchRate = 200
    xerneas_stats.evYield.hp = 3
    xerneas_stats.genderRatio = 255
    xerneas_stats.hatchCycles = 120
    xerneas_stats.baseFriendship = 0
    xerneas_stats.abilities.append("pokemon.ability.fairy_aura")
    xerneas_stats.abilities.append("")
    xerneas_stats.growthRate = _growth_indexes["GROWTH_SLOW"]

    _stats["XERNEAS"] = xerneas_stats
    _stats["XERNEAS_ACTIVE"] = xerneas_stats.__deepcopy__()

    zygarde_stats = pb_pokedex.Species()
    zygarde_stats.baseStats.hp = 108
    zygarde_stats.baseStats.attack = 100
    zygarde_stats.baseStats.defense = 121
    zygarde_stats.baseStats.speed = 95
    zygarde_stats.baseStats.specialAttack = 81
    zygarde_stats.baseStats.specialDefense = 95
    zygarde_stats.types.append("pokemon.type.dragon")
    zygarde_stats.types.append("pokemon.type.ground")
    zygarde_stats.catchRate = 200
    zygarde_stats.evYield.hp = 3
    zygarde_stats.genderRatio = 255
    zygarde_stats.hatchCycles = 120
    zygarde_stats.baseFriendship = 0
    zygarde_stats.abilities.append("pokemon.ability.power_construct")
    zygarde_stats.abilities.append("")
    zygarde_stats.growthRate = _growth_indexes["GROWTH_SLOW"]

    _stats["ZYGARDE"] = zygarde_stats
    _stats["ZYGARDE_50_POWER_CONSTRUCT"] = zygarde_stats.__deepcopy__()
    
    zygarde_10 = pb_pokedex.Species()
    zygarde_10.CopyFrom(zygarde_stats)
    zygarde_10.baseStats.hp = 54
    zygarde_10.baseStats.attack = 100
    zygarde_10.baseStats.defense = 71
    zygarde_10.baseStats.speed = 115
    zygarde_10.baseStats.specialAttack = 61
    zygarde_10.baseStats.specialDefense = 85
    
    _stats["ZYGARDE_10_POWER_CONSTRUCT"] = zygarde_10

    zygarde_10 = pb_pokedex.Species()
    zygarde_10.CopyFrom(_stats["ZYGARDE_10_POWER_CONSTRUCT"])
    zygarde_10.abilities.clear()
    zygarde_10.abilities.append("pokemon.ability.aura_break")
    zygarde_10.abilities.append("")
    _stats["ZYGARDE_10"] = zygarde_10

    oricorio_stats = pb_pokedex.Species()
    oricorio_stats.baseStats.hp = 75
    oricorio_stats.baseStats.attack = 70
    oricorio_stats.baseStats.defense = 70
    oricorio_stats.baseStats.speed = 93
    oricorio_stats.baseStats.specialAttack = 98
    oricorio_stats.baseStats.specialDefense = 70
    oricorio_stats.types.append("pokemon.type.fire")
    oricorio_stats.types.append("pokemon.type.flying")
    oricorio_stats.catchRate = 200
    oricorio_stats.evYield.specialAttack = 2
    oricorio_stats.genderRatio = poke_math.PERCENT_FEMALE(75)
    oricorio_stats.hatchCycles = 20
    oricorio_stats.baseFriendship = 70
    oricorio_stats.abilities.append("pokemon.ability.dancer")
    oricorio_stats.abilities.append("")
    oricorio_stats.growthRate = _growth_indexes["GROWTH_MEDIUM_FAST"]

    _stats["ORICORIO"] = oricorio_stats
    
    oricorio_stats = pb_pokedex.Species()
    oricorio_stats.CopyFrom(_stats["ORICORIO"])
    oricorio_stats.types.clear()
    oricorio_stats.types.append("pokemon.type.electric")
    oricorio_stats.types.append("pokemon.type.flying")
    
    _stats["ORICORIO_POM_POM"] = oricorio_stats

    oricorio_stats = pb_pokedex.Species()
    oricorio_stats.CopyFrom(_stats["ORICORIO"])
    oricorio_stats.types.clear()
    oricorio_stats.types.append("pokemon.type.psychic")
    oricorio_stats.types.append("pokemon.type.flying")

    _stats["ORICORIO_PAU"] = oricorio_stats

    oricorio_stats = pb_pokedex.Species()
    oricorio_stats.CopyFrom(_stats["ORICORIO"])
    oricorio_stats.types.clear()
    oricorio_stats.types.append("pokemon.type.ghost")
    oricorio_stats.types.append("pokemon.type.flying")

    _stats["ORICORIO_SENSU"] = oricorio_stats

    rockruff_stats = pb_pokedex.Species()
    rockruff_stats.baseStats.hp = 45
    rockruff_stats.baseStats.attack = 65
    rockruff_stats.baseStats.defense = 40
    rockruff_stats.baseStats.speed = 60
    rockruff_stats.baseStats.specialAttack = 30
    rockruff_stats.baseStats.specialDefense = 40
    rockruff_stats.types.append("pokemon.type.rock")
    rockruff_stats.catchRate = 200
    rockruff_stats.evYield.attack = 1
    rockruff_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    rockruff_stats.hatchCycles = 15
    rockruff_stats.baseFriendship = 70
    rockruff_stats.abilities.append("pokemon.ability.keen_eye")
    rockruff_stats.abilities.append("pokemon.ability.vital_spirit")
    rockruff_stats.abilities.append("pokemon.ability.steadfast")
    rockruff_stats.growthRate = _growth_indexes["GROWTH_MEDIUM_FAST"]

    _stats["ROCKRUFF"] = rockruff_stats
    
    rockruff_owntempo = pb_pokedex.Species()
    rockruff_owntempo.CopyFrom(rockruff_stats)
    rockruff_owntempo.abilities.clear()
    rockruff_owntempo.abilities.append("pokemon.ability.own_tempo")
    rockruff_owntempo.abilities.append("")
    
    _stats["ROCKRUFF_OWN_TEMPO"] = rockruff_owntempo

    mimikyu_stats = pb_pokedex.Species()
    mimikyu_stats.baseStats.hp = 55
    mimikyu_stats.baseStats.attack = 90
    mimikyu_stats.baseStats.defense = 80
    mimikyu_stats.baseStats.speed = 96
    mimikyu_stats.baseStats.specialAttack = 50
    mimikyu_stats.baseStats.specialDefense = 105
    mimikyu_stats.types.append("pokemon.type.ghost")
    mimikyu_stats.types.append("pokemon.type.fairy")
    mimikyu_stats.catchRate = 200
    mimikyu_stats.evYield.specialDefense = 2
    mimikyu_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    mimikyu_stats.hatchCycles = 20
    mimikyu_stats.baseFriendship = 70
    mimikyu_stats.abilities.append("pokemon.ability.disguise")
    mimikyu_stats.abilities.append("")
    mimikyu_stats.growthRate = _growth_indexes["GROWTH_MEDIUM_FAST"]

    _stats["MIMIKYU"] = mimikyu_stats
    _stats["MIMIKYU_BUSTED"] = mimikyu_stats.__deepcopy__()

    magearna_stats = pb_pokedex.Species()
    magearna_stats.baseStats.hp = 80
    magearna_stats.baseStats.attack = 95
    magearna_stats.baseStats.defense = 115
    magearna_stats.baseStats.speed = 65
    magearna_stats.baseStats.specialAttack = 130
    magearna_stats.baseStats.specialDefense = 115
    magearna_stats.types.append("pokemon.type.steel")
    magearna_stats.types.append("pokemon.type.fairy")
    magearna_stats.catchRate = 200
    magearna_stats.evYield.specialAttack = 3
    magearna_stats.genderRatio = 255
    magearna_stats.hatchCycles = 120
    magearna_stats.baseFriendship = 0
    magearna_stats.abilities.append("pokemon.ability.clear_body")
    magearna_stats.abilities.append("")
    magearna_stats.abilities.append("pokemon.ability.soul_heart")
    magearna_stats.growthRate = _growth_indexes["GROWTH_SLOW"]

    _stats["MAGEARNA"] = magearna_stats
    _stats["MAGEARNA_ORIGINAL_COLOR"] = magearna_stats.__deepcopy__()

    cramorant_stats = pb_pokedex.Species()
    cramorant_stats.baseStats.hp = 70
    cramorant_stats.baseStats.attack = 85
    cramorant_stats.baseStats.defense = 55
    cramorant_stats.baseStats.speed = 85
    cramorant_stats.baseStats.specialAttack = 85
    cramorant_stats.baseStats.specialDefense = 95
    cramorant_stats.types.append("pokemon.type.flying")
    cramorant_stats.types.append("pokemon.type.water")
    cramorant_stats.catchRate = 200
    cramorant_stats.evYield.specialDefense = 2
    cramorant_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    cramorant_stats.hatchCycles = 120
    cramorant_stats.baseFriendship = 70
    cramorant_stats.abilities.append("pokemon.ability.gulp_missile")
    cramorant_stats.abilities.append("")
    cramorant_stats.growthRate = _growth_indexes["GROWTH_MEDIUM_FAST"]

    _stats["CRAMORANT"] = cramorant_stats
    _stats["CRAMORANT_GULPING"] = cramorant_stats.__deepcopy__()
    _stats["CRAMORANT_GORGING"] = cramorant_stats.__deepcopy__()

    toxtricity_stats = pb_pokedex.Species()
    toxtricity_stats.baseStats.hp = 75
    toxtricity_stats.baseStats.attack = 98
    toxtricity_stats.baseStats.defense = 70
    toxtricity_stats.baseStats.speed = 75
    toxtricity_stats.baseStats.specialAttack = 114
    toxtricity_stats.baseStats.specialDefense = 70
    toxtricity_stats.types.append("pokemon.type.electric")
    toxtricity_stats.types.append("pokemon.type.poison")
    toxtricity_stats.catchRate = 200
    toxtricity_stats.evYield.specialAttack = 2
    toxtricity_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    toxtricity_stats.hatchCycles = 25
    toxtricity_stats.baseFriendship = 70
    toxtricity_stats.abilities.append("pokemon.ability.punk_rock")
    toxtricity_stats.abilities.append("")
    toxtricity_stats.abilities.append("pokemon.ability.technician")
    toxtricity_stats.growthRate = _growth_indexes["GROWTH_MEDIUM_SLOW"]

    _stats["TOXTRICITY"] = toxtricity_stats
    _stats["TOXTRICITY_LOW_KEY"] = toxtricity_stats.__deepcopy__()

    sinistea_stats = pb_pokedex.Species()
    sinistea_stats.baseStats.hp = 40
    sinistea_stats.baseStats.attack = 45
    sinistea_stats.baseStats.defense = 45
    sinistea_stats.baseStats.speed = 50
    sinistea_stats.baseStats.specialAttack = 74
    sinistea_stats.baseStats.specialDefense = 54
    sinistea_stats.types.append("pokemon.type.ghost")
    sinistea_stats.catchRate = 200
    sinistea_stats.evYield.specialAttack = 1
    sinistea_stats.genderRatio = 255
    sinistea_stats.hatchCycles = 20
    sinistea_stats.baseFriendship = 70
    sinistea_stats.abilities.append("pokemon.ability.weak_armor")
    sinistea_stats.abilities.append("")
    sinistea_stats.abilities.append("pokemon.ability.cursed_body")
    sinistea_stats.growthRate = _growth_indexes["GROWTH_MEDIUM_FAST"]

    _stats["SINISTEA"] = sinistea_stats
    _stats["SINISTEA_ANTIQUE"] = sinistea_stats.__deepcopy__()

    polteageist_stats = pb_pokedex.Species()
    polteageist_stats.baseStats.hp = 60
    polteageist_stats.baseStats.attack = 65
    polteageist_stats.baseStats.defense = 65
    polteageist_stats.baseStats.speed = 70
    polteageist_stats.baseStats.specialAttack = 134
    polteageist_stats.baseStats.specialDefense = 114
    polteageist_stats.types.append("pokemon.type.ghost")
    polteageist_stats.catchRate = 200
    polteageist_stats.evYield.specialAttack = 2
    polteageist_stats.genderRatio = 255
    polteageist_stats.hatchCycles = 20
    polteageist_stats.baseFriendship = 70
    polteageist_stats.abilities.append("pokemon.ability.weak_armor")
    polteageist_stats.abilities.append("")
    polteageist_stats.abilities.append("pokemon.ability.cursed_body")
    polteageist_stats.growthRate = _growth_indexes["GROWTH_MEDIUM_FAST"]

    _stats["POLTEAGEIST"] = polteageist_stats
    _stats["POLTEAGEIST_ANTIQUE"] = polteageist_stats.__deepcopy__()

    alcremie_stats = pb_pokedex.Species()
    alcremie_stats.baseStats.hp = 65
    alcremie_stats.baseStats.attack = 60
    alcremie_stats.baseStats.defense = 75
    alcremie_stats.baseStats.speed = 64
    alcremie_stats.baseStats.specialAttack = 110
    alcremie_stats.baseStats.specialDefense = 121
    alcremie_stats.types.append("pokemon.type.fairy")
    alcremie_stats.catchRate = 200
    alcremie_stats.evYield.specialDefense = 2
    alcremie_stats.genderRatio = 254
    alcremie_stats.hatchCycles = 20
    alcremie_stats.baseFriendship = 70
    alcremie_stats.abilities.append("pokemon.ability.sweet_veil")
    alcremie_stats.abilities.append("")
    alcremie_stats.abilities.append("pokemon.ability.aroma_veil")
    alcremie_stats.growthRate = _growth_indexes["GROWTH_MEDIUM_FAST"]

    _stats["ALCREMIE"] = alcremie_stats

    morpeko_stats = pb_pokedex.Species()
    morpeko_stats.baseStats.hp = 58
    morpeko_stats.baseStats.attack = 95
    morpeko_stats.baseStats.defense = 58
    morpeko_stats.baseStats.speed = 97
    morpeko_stats.baseStats.specialAttack = 70
    morpeko_stats.baseStats.specialDefense = 58
    morpeko_stats.types.append("pokemon.type.electric")
    morpeko_stats.types.append("pokemon.type.dark")
    morpeko_stats.catchRate = 200
    morpeko_stats.evYield.speed = 2
    morpeko_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    morpeko_stats.hatchCycles = 10
    morpeko_stats.baseFriendship = 70
    morpeko_stats.abilities.append("pokemon.ability.hunger_switch")
    morpeko_stats.abilities.append("")
    morpeko_stats.growthRate = _growth_indexes["GROWTH_MEDIUM_FAST"]

    _stats["MORPEKO"] = morpeko_stats
    _stats["MORPEKO_HANGRY"] = morpeko_stats.__deepcopy__()

    zarude_stats = pb_pokedex.Species()
    zarude_stats.baseStats.hp = 105
    zarude_stats.baseStats.attack = 120
    zarude_stats.baseStats.defense = 105
    zarude_stats.baseStats.speed = 105
    zarude_stats.baseStats.specialAttack = 70
    zarude_stats.baseStats.specialDefense = 95
    zarude_stats.types.append("pokemon.type.dark")
    zarude_stats.types.append("pokemon.type.grass")
    zarude_stats.catchRate = 200
    zarude_stats.evYield.attack = 3
    zarude_stats.genderRatio = 255
    zarude_stats.hatchCycles = 120
    zarude_stats.baseFriendship = 0
    zarude_stats.abilities.append("pokemon.ability.leaf_guard")
    zarude_stats.abilities.append("")
    zarude_stats.growthRate = _growth_indexes["GROWTH_SLOW"]

    _stats["ZARUDE"] = zarude_stats
    _stats["ZARUDE_DADA"] = zarude_stats.__deepcopy__()

    maushold_stats = pb_pokedex.Species()
    maushold_stats.baseStats.hp = 74
    maushold_stats.baseStats.attack = 75
    maushold_stats.baseStats.defense = 70
    maushold_stats.baseStats.speed = 111
    maushold_stats.baseStats.specialAttack = 65
    maushold_stats.baseStats.specialDefense = 75
    maushold_stats.types.append("pokemon.type.normal")
    maushold_stats.catchRate = 200
    maushold_stats.evYield.speed = 2
    maushold_stats.genderRatio = 255
    maushold_stats.hatchCycles = 10
    maushold_stats.baseFriendship = 50
    maushold_stats.abilities.append("pokemon.ability.technician")
    maushold_stats.abilities.append("pokemon.ability.technician")
    maushold_stats.abilities.append("pokemon.ability.friend_guard")
    maushold_stats.growthRate = _growth_indexes["GROWTH_FAST"]

    _stats["MAUSHOLD"] = maushold_stats
    _stats["MAUSHOLD_FAMILY_OF_THREE"] = maushold_stats.__deepcopy__()

    tatsugiri_stats = pb_pokedex.Species()
    tatsugiri_stats.baseStats.hp = 68
    tatsugiri_stats.baseStats.attack = 50
    tatsugiri_stats.baseStats.defense = 60
    tatsugiri_stats.baseStats.speed = 82
    tatsugiri_stats.baseStats.specialAttack = 120
    tatsugiri_stats.baseStats.specialDefense = 95
    tatsugiri_stats.types.append("pokemon.type.dragon")
    tatsugiri_stats.types.append("pokemon.type.water")
    tatsugiri_stats.catchRate = 200
    tatsugiri_stats.evYield.specialAttack = 2
    tatsugiri_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    tatsugiri_stats.hatchCycles = 35
    tatsugiri_stats.baseFriendship = 50
    tatsugiri_stats.abilities.append("pokemon.ability.swift_swim")
    tatsugiri_stats.abilities.append("pokemon.ability.swift_swim")
    tatsugiri_stats.abilities.append("pokemon.ability.commander")
    tatsugiri_stats.growthRate = _growth_indexes["GROWTH_MEDIUM_SLOW"]

    _stats["TATSUGIRI"] = tatsugiri_stats
    _stats["TATSUGIRI_DROOPY"] = tatsugiri_stats.__deepcopy__()
    _stats["TATSUGIRI_STRETCHY"] = tatsugiri_stats.__deepcopy__()

    dudunsparce_stats = pb_pokedex.Species()
    dudunsparce_stats.baseStats.hp = 125
    dudunsparce_stats.baseStats.attack = 100
    dudunsparce_stats.baseStats.defense = 80
    dudunsparce_stats.baseStats.speed = 55
    dudunsparce_stats.baseStats.specialAttack = 85
    dudunsparce_stats.baseStats.specialDefense = 75
    dudunsparce_stats.types.append("pokemon.type.normal")
    dudunsparce_stats.catchRate = 200
    dudunsparce_stats.evYield.hp = 2
    dudunsparce_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    dudunsparce_stats.hatchCycles = 20
    dudunsparce_stats.baseFriendship = 50
    dudunsparce_stats.abilities.append("pokemon.ability.serene_grace")
    dudunsparce_stats.abilities.append("")
    dudunsparce_stats.abilities.append("pokemon.ability.rattled")
    dudunsparce_stats.growthRate = _growth_indexes["GROWTH_MEDIUM_FAST"]

    _stats["DUDUNSPARCE"] = dudunsparce_stats
    _stats["DUDUNSPARCE_THREE_SEGMENT"] = dudunsparce_stats.__deepcopy__()

    poltchageist_stats = pb_pokedex.Species()
    poltchageist_stats.baseStats.hp = 40
    poltchageist_stats.baseStats.attack = 45
    poltchageist_stats.baseStats.defense = 45
    poltchageist_stats.baseStats.speed = 50
    poltchageist_stats.baseStats.specialAttack = 74
    poltchageist_stats.baseStats.specialDefense = 54
    poltchageist_stats.types.append("pokemon.type.grass")
    poltchageist_stats.types.append("pokemon.type.ghost")
    poltchageist_stats.catchRate = 120
    poltchageist_stats.evYield.specialAttack = 1
    poltchageist_stats.genderRatio = 255
    poltchageist_stats.hatchCycles = 20
    poltchageist_stats.baseFriendship = 70
    poltchageist_stats.abilities.append("pokemon.ability.hospitality")
    poltchageist_stats.abilities.append("")
    poltchageist_stats.abilities.append("pokemon.ability.heatproof")
    poltchageist_stats.growthRate = _growth_indexes["GROWTH_MEDIUM_FAST"]

    _stats["POLTCHAGEIST"] = poltchageist_stats

    sinistcha_stats = pb_pokedex.Species()
    sinistcha_stats.baseStats.hp = 71
    sinistcha_stats.baseStats.attack = 60
    sinistcha_stats.baseStats.defense = 106
    sinistcha_stats.baseStats.speed = 70
    sinistcha_stats.baseStats.specialAttack = 121
    sinistcha_stats.baseStats.specialDefense = 80
    sinistcha_stats.types.append("pokemon.type.grass")
    sinistcha_stats.types.append("pokemon.type.ghost")
    sinistcha_stats.catchRate = 60
    sinistcha_stats.evYield.specialAttack = 2
    sinistcha_stats.genderRatio = 255
    sinistcha_stats.hatchCycles = 20
    sinistcha_stats.baseFriendship = 70
    sinistcha_stats.abilities.append("pokemon.ability.hospitality")
    sinistcha_stats.abilities.append("")
    sinistcha_stats.abilities.append("pokemon.ability.heatproof")
    sinistcha_stats.growthRate = _growth_indexes["GROWTH_MEDIUM_FAST"]

    _stats["SINISTCHA"] = sinistcha_stats
    
    rotom_heat = pb_pokedex.Species()
    rotom_heat.CopyFrom(_stats["ROTOM"])
    rotom_heat.types.clear()
    rotom_heat.types.append("pokemon.type.electric")
    rotom_heat.types.append("pokemon.type.fire")
    _stats["ROTOM_HEAT"] = rotom_heat
    
    rotom_heat = pb_pokedex.Species()
    rotom_heat.CopyFrom(_stats["ROTOM"])
    rotom_heat.types.clear()
    rotom_heat.types.append("pokemon.type.electric")
    rotom_heat.types.append("pokemon.type.water")
    _stats["ROTOM_WASH"] = rotom_heat
    
    rotom_heat = pb_pokedex.Species()
    rotom_heat.CopyFrom(_stats["ROTOM"])
    rotom_heat.types.clear()
    rotom_heat.types.append("pokemon.type.electric")
    rotom_heat.types.append("pokemon.type.ice")
    _stats["ROTOM_FROST"] = rotom_heat

    rotom_heat = pb_pokedex.Species()
    rotom_heat.CopyFrom(_stats["ROTOM"])
    rotom_heat.types.clear()
    rotom_heat.types.append("pokemon.type.electric")
    rotom_heat.types.append("pokemon.type.flying")
    _stats["ROTOM_FAN"] = rotom_heat

    rotom_heat = pb_pokedex.Species()
    rotom_heat.CopyFrom(_stats["ROTOM"])
    rotom_heat.types.clear()
    rotom_heat.types.append("pokemon.type.electric")
    rotom_heat.types.append("pokemon.type.grass")
    _stats["ROTOM_MOW"] = rotom_heat



    wooper_stats = _stats["WOOPER"]
    wooper_stats.baseStats.hp = 55
    wooper_stats.baseStats.attack = 45
    wooper_stats.baseStats.defense = 45
    wooper_stats.baseStats.speed = 15
    wooper_stats.baseStats.specialAttack = 25
    wooper_stats.baseStats.specialDefense = 25
    wooper_stats.catchRate = 200
    wooper_stats.evYield.hp = 1
    wooper_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    wooper_stats.hatchCycles = 20
    wooper_stats.baseFriendship = 70
    wooper_stats.growthRate = _growth_indexes["GROWTH_MEDIUM_FAST"]


    wooper_stats = _stats["WOOPER_PALDEAN"]
    wooper_stats.baseStats.hp = 55
    wooper_stats.baseStats.attack = 45
    wooper_stats.baseStats.defense = 45
    wooper_stats.baseStats.speed = 15
    wooper_stats.baseStats.specialAttack = 25
    wooper_stats.baseStats.specialDefense = 25
    wooper_stats.catchRate = 200
    wooper_stats.evYield.hp = 1
    wooper_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    wooper_stats.hatchCycles = 20
    wooper_stats.baseFriendship = 70
    wooper_stats.growthRate = _growth_indexes["GROWTH_MEDIUM_FAST"]
    

    squawkabilly_stats = _stats["SQUAWKABILLY"]
    squawkabilly_stats.baseStats.hp = 82
    squawkabilly_stats.baseStats.attack = 96
    squawkabilly_stats.baseStats.defense = 51
    squawkabilly_stats.baseStats.speed = 92
    squawkabilly_stats.baseStats.specialAttack = 45
    squawkabilly_stats.baseStats.specialDefense = 51
    sinistcha_stats.types.append("pokemon.type.normal")
    sinistcha_stats.types.append("pokemon.type.flying")
    squawkabilly_stats.catchRate = 200
    squawkabilly_stats.evYield.attack = 1
    squawkabilly_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    squawkabilly_stats.hatchCycles = 15
    squawkabilly_stats.baseFriendship = 50
    squawkabilly_stats.growthRate = _growth_indexes["GROWTH_ERRATIC"]

    squawkabilly_stats = _stats["SQUAWKABILLY_BLUE_PLUMAGE"]
    squawkabilly_stats.baseStats.hp = 82
    squawkabilly_stats.baseStats.attack = 96
    squawkabilly_stats.baseStats.defense = 51
    squawkabilly_stats.baseStats.speed = 92
    squawkabilly_stats.baseStats.specialAttack = 45
    squawkabilly_stats.baseStats.specialDefense = 51
    sinistcha_stats.types.append("pokemon.type.normal")
    sinistcha_stats.types.append("pokemon.type.flying")
    squawkabilly_stats.catchRate = 200
    squawkabilly_stats.evYield.attack = 1
    squawkabilly_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    squawkabilly_stats.hatchCycles = 15
    squawkabilly_stats.baseFriendship = 50
    squawkabilly_stats.growthRate = _growth_indexes["GROWTH_ERRATIC"]

    squawkabilly_stats = _stats["SQUAWKABILLY_YELLOW_PLUMAGE"]
    squawkabilly_stats.baseStats.hp = 82
    squawkabilly_stats.baseStats.attack = 96
    squawkabilly_stats.baseStats.defense = 51
    squawkabilly_stats.baseStats.speed = 92
    squawkabilly_stats.baseStats.specialAttack = 45
    squawkabilly_stats.baseStats.specialDefense = 51
    sinistcha_stats.types.append("pokemon.type.normal")
    sinistcha_stats.types.append("pokemon.type.flying")
    squawkabilly_stats.catchRate = 200
    squawkabilly_stats.evYield.attack = 1
    squawkabilly_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    squawkabilly_stats.hatchCycles = 15
    squawkabilly_stats.baseFriendship = 50
    squawkabilly_stats.growthRate = _growth_indexes["GROWTH_ERRATIC"]

    squawkabilly_stats = _stats["SQUAWKABILLY_WHITE_PLUMAGE"]
    squawkabilly_stats.baseStats.hp = 82
    squawkabilly_stats.baseStats.attack = 96
    squawkabilly_stats.baseStats.defense = 51
    squawkabilly_stats.baseStats.speed = 92
    squawkabilly_stats.baseStats.specialAttack = 45
    squawkabilly_stats.baseStats.specialDefense = 51
    sinistcha_stats.types.append("pokemon.type.normal")
    sinistcha_stats.types.append("pokemon.type.flying")
    squawkabilly_stats.catchRate = 200
    squawkabilly_stats.evYield.attack = 1
    squawkabilly_stats.genderRatio = poke_math.PERCENT_FEMALE(50)
    squawkabilly_stats.hatchCycles = 15
    squawkabilly_stats.baseFriendship = 50
    squawkabilly_stats.growthRate = _growth_indexes["GROWTH_ERRATIC"]

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
    print("Generating Pokedex")

    sprite_dir = directories.get_output_dir("pokemon_null/assets/pokemon")

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
                stats.sprites.party = f"pokelink-community:/pokemon_null/assets/pokemon/party/{file_form_id}.gif"
            elif os.path.isfile(os.path.join(sprite_dir, "shiny",
                                             f"{file_id}-gmax.gif")) and species != "EEVEE":
                stats.sprites.normal = f"pokelink-community:/pokemon_null/assets/pokemon/party/{file_id}-gmax.gif"
            elif os.path.isfile(
                    os.path.join(sprite_dir, "party", f"{file_id}.gif")):
                stats.sprites.party = f"pokelink-community:/pokemon_null/assets/pokemon/party/{file_id}.gif"
            else:
                print(
                    f"\tWARNING: Not able to find a party sprite for {file_form_id}")

            if os.path.isfile(
                    os.path.join(sprite_dir, "normal", f"{file_form_id}.png")):
                stats.sprites.normal = f"pokelink-community:/pokemon_null/assets/pokemon/normal/{file_form_id}.png"
            elif os.path.isfile(os.path.join(sprite_dir, "normal",
                                             f"{file_id}-gmax.png")) and species != "EEVEE":
                stats.sprites.normal = f"pokelink-community:/pokemon_null/assets/pokemon/normal/{file_id}-gmax.png"
            elif os.path.isfile(
                    os.path.join(sprite_dir, "normal", f"{file_id}.png")):
                stats.sprites.normal = f"pokelink-community:/pokemon_null/assets/pokemon/normal/{file_id}.png"
            else:
                print(
                    f"\tWARNING: Not able to find a normal sprite for {file_form_id}")

            if os.path.isfile(
                    os.path.join(sprite_dir, "shiny", f"{file_form_id}.png")):
                stats.sprites.shiny = f"pokelink-community:/pokemon_null/assets/pokemon/shiny/{file_form_id}.png"
            elif os.path.isfile(os.path.join(sprite_dir, "shiny",
                                             f"{file_id}-gmax.png")) and species != "EEVEE":
                stats.sprites.shiny = f"pokelink-community:/pokemon_null/assets/pokemon/shiny/{file_id}-gmax.png"
            elif os.path.isfile(
                    os.path.join(sprite_dir, "shiny", f"{file_id}.png")):
                stats.sprites.shiny = f"pokelink-community:/pokemon_null/assets/pokemon/shiny/{file_id}.png"
            else:
                print(
                    f"\tWARNING: Not able to find a shiny sprite for {file_form_id}")

            if os.path.isfile(os.path.join(sprite_dir, "normal",
                                           f"{file_form_id}-f.png")) and stats.genderRatio != 0 and stats.genderRatio != 255:
                stats.sprites.female = f"pokelink-community:/pokemon_null/assets/pokemon/normal/{file_form_id}-f.png"

            if os.path.isfile(os.path.join(sprite_dir, "shiny",
                                           f"{file_form_id}-f.png")) and stats.genderRatio != 0 and stats.genderRatio != 255:
                stats.sprites.femaleShiny = f"pokelink-community:/pokemon_null/assets/pokemon/shiny/{file_form_id}-f.png"

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
                        f"Null.Form.{game_strings.clean_up(form_translation)}",
                        form_translation)
                    stats.formName = f"Null.Form.{game_strings.clean_up(form_translation)}"

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
        os.path.join(directories.get_output_dir("pokemon_null", True),
                     "null.dex"), json_format.MessageToDict(_dex))
