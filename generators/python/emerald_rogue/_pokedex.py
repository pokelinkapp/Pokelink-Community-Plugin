import collections

import pokelink.proto.v0_7_1.pokedex_pb2 as pb_pokedex
import pokelink.directories as directories
import pokelink.translations as translations
from google.protobuf import json_format

from emerald_rogue._items import get_item_string
from emerald_rogue._moves import get_move_string
from emerald_rogue import RogueVersion
from pokelink import strip_comments, game_strings, core_plugin
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

_def_replacements = dict()
_def_replacements_args = dict()

_growth_indexes = {
    "GROWTH_MEDIUM_FAST": 0,
    "GROWTH_ERRATIC": 1,
    "GROWTH_FLUCTUATING": 2,
    "GROWTH_MEDIUM_SLOW": 3,
    "GROWTH_FAST": 4,
    "GROWTH_SLOW": 5
}


def process_species_forms(version: RogueVersion):
    global _species_form_id
    last_id = 0
    print("\tProcessing Species and Forms")
    with open(os.path.join(directories.get_external_dir("emerald-rogue"),
                           "vanilla" if version == RogueVersion.VANILLA else "expansion",
                           "include", "constants", "species.h"), "r") as file:

        internal_lines = [strip_comments(line) for line in file]

        offset = 0

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

            if species == "VENUSAUR_MEGA":
                offset = 905
            elif species == "SPRIGATITO":
                offset += 383
            elif species == "LUGIA_SHADOW":
                offset += 146
            elif species == "VENUSAUR_GIGANTAMAX":
                offset += 54
            elif species == "WOBBUFFET_PUNCHING":
                offset += 34

            if items[1].startswith("SPECIES_UNOWN") or items[1].startswith(
                    "SPECIES_OLD_UNOWN"):
                internal_id = last_id + 1

                if species.endswith("EMARK"):
                    species = "UNOWN_EXCLAMATION"
                elif species.endswith("QMARK"):
                    species = "UNOWN_QUESTION"
            else:
                internal_id = int(items[-1]) + offset

            last_id = internal_id

            _species_form_id[species] = internal_id

            if not game_strings.has_species(
                    species) and species != "NIDORAN_F" and species != "NIDORAN_M" and species != "TYPE_NULL" and species != "MR_MIME_GALARIAN" and species != "MIME_JR":
                split = species.split("_")
                mon = split[0]
                form = str.join("_", split[1:])

                if not _species_forms.__contains__(mon):
                    _species_forms[mon] = dict()
                    _species_forms[mon][form] = 0
                else:
                    _species_forms[mon][form] = len(_species_forms[mon])
            elif species == "MR_MIME_GALARIAN":
                split = species.split("_")
                mon = "MR_MIME"
                form = "GALARIAN"

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


def process_national_dex_ids(version: RogueVersion):
    global _dex_ids
    print("\tProcessing National Dex IDs")
    with open(os.path.join(directories.get_external_dir("emerald-rogue"),
                           "vanilla" if version == RogueVersion.VANILLA else "expansion",
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

            if species.startswith("OLD_UNOWN"):
                continue

            _dex_ids[dex_id] = species
            dex_id += 1

        print(f"\t\tFound {_dex_ids.__len__():n} dex ids")


def get_pokemon_number(line: str) -> int:
    try:
        return int(line.split(" ")[-1].removesuffix(","))
    except:
        return int(line.split(" ")[-3])


def process_species_stats(version: RogueVersion):
    global _stats
    print("\tProcessing Stats")

    lines = []

    for info in ([
        "species_info/gen_1.h", "species_info/gen_2.h",
        "species_info/gen_3.h", "species_info/gen_4.h",
        "species_info/gen_5.h", "species_info/gen_6.h",
        "species_info/gen_7.h", "species_info/gen_8.h",
        "species_info/gen_9.h"
    ] if version == RogueVersion.EXPANSION else ["base_stats.h"]):
        with open(os.path.join(directories.get_external_dir("emerald-rogue"),
                               "vanilla" if version == RogueVersion.VANILLA else "expansion",
                               "src", "data", "pokemon", info), "r") as file:
            lines += [strip_comments(line) for line in file]

    if version == RogueVersion.EXPANSION:
        temp_lines = str.join("\n", lines)

        def_name: str | None = None
        def_lines: str | None = None
        def_args: list[str] | None = None

        for line in temp_lines.split("\n"):
            line_clean = line.strip()

            if def_name is not None:
                def_lines += line_clean.replace("\\", "\n")

                if not line_clean.endswith("\\"):
                    if def_args is None:
                        _def_replacements[def_name] = def_lines
                    else:
                        _def_replacements_args[def_name] = (def_args, def_lines)
                    def_name = None
                    def_lines = None
                    def_args = None
            elif line_clean.startswith("#define"):
                split = line_clean.split(" ")
                if str.join(" ", split[1:6]).strip().endswith(")"):
                    brackets = str.join(" ", split[1:6]).split("(")
                    def_args = brackets[1].removesuffix(")").replace(" ",
                                                                     "").split(
                        ",")
                    def_name = brackets[0]
                    def_lines = ""
                elif line_clean.endswith("\\"):
                    def_name = split[1]
                    def_lines = ""
                else:
                    _def_replacements[split[1]] = str.join(" ", split[2:])

        for i in range(2):
            param_lines = ""
            for line in temp_lines.split("\n"):
                line_clean = line.strip()
                for replace in _def_replacements_args:
                    if line_clean.__contains__("= " + replace):
                        split = line_clean.split(replace)

                        args = split[1].removeprefix("(").removesuffix(
                            "),").replace(" ", "").split(",")

                        replace_args, replacement = _def_replacements_args[
                            replace]

                        for i in range(args.__len__()):
                            replacement = replacement.replace(
                                f"##{replace_args[i]}##", f"{args[i]}")
                            replacement = replacement.replace(
                                f"#{replace_args[i]}", f"{args[i]}")
                            replacement = replacement.replace(
                                f" {replace_args[i]}", f" {args[i]}")

                        prefix = split[0]

                        while prefix.__contains__("  "):
                            prefix = prefix.replace("  ", " ")

                        line_clean = f"{prefix}\n{replacement},\n"

                        break
                    elif line_clean.startswith(replace):
                        split = line_clean.split(replace)

                        args = split[1].removeprefix("(").removesuffix(
                            "),").replace(" ", "").split(",")

                        replace_args, replacement = _def_replacements_args[
                            replace]

                        for i in range(replace_args.__len__()):
                            replacement = replacement.replace(
                                f" ##{replace_args[i]}##", f"{args[i]}")
                            replacement = replacement.replace(
                                f" #{replace_args[i]}", f"{args[i]}")
                            replacement = replacement.replace(
                                f" {replace_args[i]}", f" {args[i]}")

                        line_clean = f"{replacement},\n"

                param_lines += f"{line_clean}\n"

            temp_lines = param_lines

            for replace in _def_replacements:
                temp_lines = temp_lines.replace(replace,
                                                _def_replacements[replace])

        lines = temp_lines.split("\n")

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
            elif line.startswith(".type1"):
                type = line.removeprefix(".type1 = ").removesuffix(",")
                current_pokemon.types.insert(0,
                                             f"pokemon.type.{type.lower().removeprefix("type_")}")
            elif line.startswith(".type2"):
                type = line.removeprefix(".type2 = ").removesuffix(",")
                current_pokemon.types.append(
                    f"pokemon.type.{type.lower().removeprefix("type_")}")
            elif line.startswith(".types"):
                types = line.removeprefix(".types = { ").removesuffix(
                    " },").split(", ")

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
                            f"EmeraldRogue.Ability.{game_strings.clean_up(ability.removeprefix("ABILITY_"))}")
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
    unown_stat.abilities.append("")

    _stats["UNOWN"] = unown_stat

    for form in "B|C|D|E|F|G|H|I|J|K|L|M|N|O|P|Q|R|S|T|U|V|W|X|Y|Z".split(
            "|") + [
                    "EXCLAMATION", "QUESTION"
                ]:
        form_stat = pb_pokedex.Species()
        form_stat.CopyFrom(unown_stat)
        _stats[f"UNOWN_{form}"] = form_stat

    if version == RogueVersion.EXPANSION:
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
                        f"pokemon.ability.{"embody_aspect_teal_mask" if tera == "_TERA" else "defiant"}")
                    form_stat.abilities.append("")
                    form_stat.abilities.append(
                        f"pokemon.ability.{"embody_aspect_teal_mask" if tera == "_TERA" else "defiant"}")
                elif form == "WELLSPRING":
                    form_stat.types.append("pokemon.type.water")
                    form_stat.abilities.append(
                        f"pokemon.ability.{"embody_aspect_wellspring_mask" if tera == "_TERA" else "water_absorb"}")
                    form_stat.abilities.append("")
                    form_stat.abilities.append(
                        f"pokemon.ability.{"embody_aspect_wellspring_mask" if tera == "_TERA" else "water_absorb"}")
                elif form == "HEARTHFLAME":
                    form_stat.types.append("pokemon.type.fire")
                    form_stat.abilities.append(
                        f"pokemon.ability.{"embody_aspect_hearthflame_mask" if tera == "_TERA" else "mold_breaker"}")
                    form_stat.abilities.append("")
                    form_stat.abilities.append(
                        f"pokemon.ability.{"embody_aspect_hearthflame_mask" if tera == "_TERA" else "mold_breaker"}")
                elif form == "CORNERSTONE":
                    form_stat.types.append("pokemon.type.rock")
                    form_stat.abilities.append(
                        f"pokemon.ability.{"embody_aspect_cornerstone_mask" if tera == "_TERA" else "sturdy"}")
                    form_stat.abilities.append("")
                    form_stat.abilities.append(
                        f"pokemon.ability.{"embody_aspect_cornerstone_mask" if tera == "_TERA" else "sturdy"}")

                _stats[f"OGERPON_{form}_MASK{tera}"] = form_stat

        white_flabebe = pb_pokedex.Species()
        white_flabebe.CopyFrom(_stats["FLABEBE_BLUE_FLOWER"])
        white_flabebe.gameId += 1
        white_flabebe.form += 1
        white_flabebe.formName = "pokemon.form.white"
        _stats["FLABEBE_WHITE_FLOWER"] = white_flabebe

        _evolutions["BISHARP"] = [["EVO_ITEM", "ITEM_LEADERS_CREST", "KINGAMBIT"]]
        _evolutions["PAWMO"] = [["EVO_LEVEL", "20", "PAWMOT"]]
        _evolutions["BRAMBLIN"] = [["EVO_LEVEL", "20", "BRAMBLEGHAST"]]
        _evolutions["RELLOR"] = [["EVO_LEVEL", "20", "RABSCA"]]
        _evolutions["GIMMIGHOUL"] = [["EVO_ITEM", "ITEM_GIMMIGHOUL_COIN", "GHOLDENGO"]]


def process(version: RogueVersion):
    _species_form_id.clear()
    _species_forms.clear()
    _dex_ids.clear()
    _dex.ClearField("entries")
    _stats.clear()
    _def_replacements.clear()
    print("Processing Pokedex")
    process_species_forms(version)
    process_national_dex_ids(version)
    process_species_stats(version)


def handle_evos(base_entry: pb_pokedex.Species, entry: pb_pokedex.Species,
                evos: list[list[str]]):
    if base_entry.id == 868:
        if base_entry.evolutions.__len__() > 0:
            return

        strawberry_vanilla: pb_pokedex.Species = _stats[
            "ALCREMIE_STRAWBERRY_VANILLA_CREAM"]
        straw_evo = pb_pokedex.Evolution()
        straw_evo.to = strawberry_vanilla.id
        straw_evo.fromForm = 0 if not entry.HasField("form") else entry.form
        straw_evo.toForm = 0 if not strawberry_vanilla.HasField(
            "form") else strawberry_vanilla.form
        straw_evo.conditions["pokemon.evolve.level"].number = 30
        base_entry.evolutions.append(straw_evo)

        berry_vanilla: pb_pokedex.Species = _stats[
            "ALCREMIE_BERRY_VANILLA_CREAM"]
        berry_evo = pb_pokedex.Evolution()
        berry_evo.to = berry_vanilla.id
        berry_evo.fromForm = 0 if not entry.HasField("form") else entry.form
        berry_evo.toForm = 0 if not berry_vanilla.HasField(
            "form") else berry_vanilla.form
        berry_evo.conditions["pokemon.evolve.level"].number = 30
        berry_evo.conditions[
            "EmeraldRogue.Evolve.hasNature"].string = "pokemon.nature.adamant"
        base_entry.evolutions.append(berry_evo)

        love_vanilla: pb_pokedex.Species = _stats["ALCREMIE_LOVE_VANILLA_CREAM"]
        love_evo = pb_pokedex.Evolution()
        love_evo.to = love_vanilla.id
        love_evo.fromForm = 0 if not entry.HasField("form") else entry.form
        love_evo.toForm = 0 if not love_vanilla.HasField(
            "form") else love_vanilla.form
        love_evo.conditions["pokemon.evolve.level"].number = 30
        love_evo.conditions[
            "EmeraldRogue.Evolve.hasNature"].string = "pokemon.nature.lax"
        base_entry.evolutions.append(love_evo)

        star_vanilla: pb_pokedex.Species = _stats["ALCREMIE_STAR_VANILLA_CREAM"]
        star_evo = pb_pokedex.Evolution()
        star_evo.to = star_vanilla.id
        star_evo.fromForm = 0 if not entry.HasField("form") else entry.form
        star_evo.toForm = 0 if not star_vanilla.HasField(
            "form") else star_vanilla.form
        star_evo.conditions["pokemon.evolve.level"].number = 30
        star_evo.conditions[
            "EmeraldRogue.Evolve.hasNature"].string = "pokemon.nature.modest"
        base_entry.evolutions.append(star_evo)

        clover_vanilla: pb_pokedex.Species = _stats[
            "ALCREMIE_CLOVER_VANILLA_CREAM"]
        clover_evo = pb_pokedex.Evolution()
        clover_evo.to = clover_vanilla.id
        clover_evo.fromForm = 0 if not entry.HasField("form") else entry.form
        clover_evo.toForm = 0 if not clover_vanilla.HasField(
            "form") else clover_vanilla.form
        clover_evo.conditions["pokemon.evolve.level"].number = 30
        clover_evo.conditions[
            "EmeraldRogue.Evolve.hasNature"].string = "pokemon.nature.gentle"
        base_entry.evolutions.append(clover_evo)

        flower_vanilla: pb_pokedex.Species = _stats[
            "ALCREMIE_FLOWER_VANILLA_CREAM"]
        flower_evo = pb_pokedex.Evolution()
        flower_evo.to = flower_vanilla.id
        flower_evo.fromForm = 0 if not entry.HasField("form") else entry.form
        flower_evo.toForm = 0 if not flower_vanilla.HasField(
            "form") else flower_vanilla.form
        flower_evo.conditions["pokemon.evolve.level"].number = 30
        flower_evo.conditions[
            "EmeraldRogue.Evolve.hasNature"].string = "pokemon.nature.timid"
        base_entry.evolutions.append(flower_evo)

        ribbon_vanilla: pb_pokedex.Species = _stats[
            "ALCREMIE_RIBBON_VANILLA_CREAM"]
        ribbon_evo = pb_pokedex.Evolution()
        ribbon_evo.to = ribbon_vanilla.id
        ribbon_evo.fromForm = 0 if not entry.HasField("form") else entry.form
        ribbon_evo.toForm = 0 if not ribbon_vanilla.HasField(
            "form") else ribbon_vanilla.form
        ribbon_evo.conditions["pokemon.evolve.level"].number = 30
        ribbon_evo.conditions[
            "EmeraldRogue.Evolve.hasNature"].string = "pokemon.nature.jolly"
        base_entry.evolutions.append(ribbon_evo)
        return

    evo_index = 0

    for evo in evos:
        target: pb_pokedex.Species = _stats[evo[2]]
        evo_data = pb_pokedex.Evolution()
        evo_data.to = target.id
        evo_data.fromForm = 0 if not entry.HasField("form") else entry.form
        evo_data.toForm = 0 if not target.HasField("form") else target.form
        append = False

        conditions = evo_data.conditions

        if entry.gameId == 298 and evo_index == 0:
            evo[0] = "EVO_LEVEL"
            evo[1] = "10"
        elif entry.gameId == 991 and evo_index == 0:
            evo[0] = "EVO_LEVEL"
            evo[1] = "34"
        elif entry.gameId == 808 and evo_index == 0:
            evo[0] = "EVO_ITEM"
            evo[1] = "ITEM_METAL_COAT"
        elif entry.gameId == 705 and evo_index == 0:
            evo[0] = "EVO_LEVEL"
        elif (entry.gameId == 705 or entry.gameId == 1005) and evo_index == 1:
            evo_index += 1
            continue
        elif entry.gameId == 891 and (evo[0] == "EVO_ITEM" or evo_index == 3):
            evo_index += 1
            continue
        elif entry.gameId == 1090:
            if evo_index == 0:
                male_basculegion: pb_pokedex.Species = _stats[
                    "BASCULEGION_MALE"]
                evo_data.to = male_basculegion.id
                evo_data.toForm = 0 if not male_basculegion.HasField(
                    "form") else male_basculegion.form

                evo[0] = "EVO_LEVEL_MALE"
                evo[1] = "36"
            if evo_index == 1:
                female_basculegion: pb_pokedex.Species = _stats[
                    "BASCULEGION_FEMALE"]
                evo_data.to = female_basculegion.id
                evo_data.toForm = 0 if not female_basculegion.HasField(
                    "form") else female_basculegion.form

                evo[0] = "EVO_LEVEL_FEMALE"
                evo[1] = "36"
        elif (
                entry.gameId == 25 or entry.gameId == 102 or entry.gameId == 104) and evo_index == 1:
            evo[0] = "EVO_ITEM"
            evo[1] = "ITEM_ALOLA_STONE"
        elif (entry.gameId == 109 or entry.gameId == 439) and evo_index == 1:
            evo[0] = "EVO_ITEM"
            evo[1] = "ITEM_GALAR_STONE"
        elif (
                entry.gameId == 156 or entry.gameId == 502 or entry.gameId == 548 or entry.gameId == 627 or entry.gameId == 704 or entry.gameId == 712 or entry.gameId == 723) and evo_index == 1:
            evo[0] = "EVO_ITEM"
            evo[1] = "ITEM_HISUI_STONE"
        elif entry.gameId == 217 and evo_index == 0:
            evo[0] = "EVO_ITEM"
            evo[1] = "ITEM_PEAT_BLOCK"
        elif entry.gameId == 217 and evo_index == 1:
            evo[0] = "EVO_ITEM"
            evo[1] = "ITEM_MOON_STONE"
        elif evo[0] == "EVO_MOVE":
            evo[0] = "EVO_LEVEL"
            evo[1] = "30"
        elif evo[0] == "EVO_ITEM" and evo[1] == "ITEM_LINK_CABLE":
            evo_index += 1
            continue
        elif evo[0] == "EVO_BEAUTY":
            evo_index += 1
            continue
        elif evo[0] == "EVO_FRIENDSHIP":
            evo[0] = "EVO_LEVEL"
            evo[1] = "30"
        elif evo[0] == "EVO_TRADE":
            evo[0] = "EVO_ITEM"
            evo[1] = "ITEM_LINK_CABLE"
        elif evo[0] == "EVO_LEVEL_ITEM" or evo[0] == "EVO_ITEM_HOLD_DAY" or evo[0] == "EVO_ITEM_HOLD_NIGHT":
            evo[0] = "EVO_ITEM"
        elif evo[0] == "EVO_FRIENDSHIP_DAY":
            if entry.gameId == 133:
                evo[0] = "EVO_ITEM"
                evo[1] = "ITEM_SUN_STONE"
            else:
                evo[0] = "EVO_LEVEL"
                evo[1] = "30"
        elif evo[0] == "EVO_FRIENDSHIP_NIGHT":
            if entry.gameId == 133:
                evo[0] = "EVO_ITEM"
                evo[1] = "ITEM_MOON_STONE"
            else:
                evo[0] = "EVO_LEVEL"
                evo[1] = "30"
        elif evo[0] == "EVO_LEVEL_DAY" or evo[0] == "EVO_LEVEL_NIGHT":
            if not entry.gameId == 744 and not entry.gameId == 790:
                evo[0] = "EVO_LEVEL"
        elif evo[0] == "EVO_TRADE_ITEM":
            evo[0] = "EVO_ITEM"
        elif evo[0] == "EVO_SPECIFIC_MON_IN_PARTY" or evo[0] == "EVO_CRITICAL_HITS" or evo[0] == "EVO_SCRIPT_TRIGGER_DMG":
            evo[0] = "EVO_LEVEL"
            evo[1] = "36"
        elif evo[0] == "EVO_WATER_SCROLL":
            evo[0] = "EVO_ITEM"
            evo[1] = "ITEM_WATER_STONE"
        elif evo[0] == "EVO_DARK_SCROLL":
            evo[0] = "EVO_ITEM"
            evo[1] = "ITEM_MOON_STONE"
        elif evo[0] == "EVO_TRADE_SPECIFIC_MON":
            evo[0] = "EVO_ITEM"
            evo[1] = "ITEM_LINK_CABLE"
        elif evo[0] == "EVO_LEVEL_RAIN" or evo[0] == "EVO_LEVEL_DARK_TYPE_MON_IN_PARTY":
            evo[0] = "EVO_LEVEL"
        elif evo[0] == "EVO_FRIENDSHIP_MOVE_TYPE":
            evo[0] = "EVO_MOVE_TYPE"
        elif evo[0] == "EVO_SPECIFIC_MAP" or evo[0] == "EVO_ITEM_NIGHT" or evo[0] == "EVO_ITEM_DAY" or evo[0] == "EVO_MAPSEC":
            evo_index += 1
            continue

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
        elif evo[0] == "EVO_MOVE_TWO_SEGMENT" or evo[
            0] == "EVO_MOVE_THREE_SEGMENT":
            move = get_move_string(evo[1].removeprefix("MOVE_"))
            if move is None:
                print(f"\tERROR: Missing move string \"{evo[1]}\"")
                exit(-1)
            conditions["pokemon.evolve.level"].number = 24
            conditions[
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
            conditions["pokemon.evolve.level"].number = int(evo[1])
        elif evo[0] == "EVO_LEVEL_SHEDINJA":
            conditions["pokemon.evolve.level"].number = int(evo[1])
            conditions["pokemon.evolve.emptySlot"].nested[
                "pokemon.evolve.hasItem"].string = "pokemon.ball.poke_ball"
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
        elif evo[0] == "EVO_CRITICAL_HITS":
            if not evo[1].isdigit():
                print(f"\tERROR: Level is not a number. Value: {evo[1]}")
                exit(-1)
            conditions["pokemon.evolve.critsInOneBattle"].number = int(evo[1])
        elif evo[0] == "EVO_ITEM_HOLD_NIGHT":
            item = get_item_string(evo[1].removeprefix("ITEM_"))
            if item is None:
                print(f"\tERROR: Missing item string \"{evo[1]}\"")
                exit(-1)

            level_up = conditions["pokemon.evolve.levelUp"].nested
            level_up["pokemon.evolve.holdItem"].string = item
            level_up["pokemon.evolve.time"].string = "timeOfDay.night"
        elif evo[0] == "EVO_ITEM_NIGHT":
            item = get_item_string(evo[1].removeprefix("ITEM_"))
            if item is None:
                print(f"\tERROR: Missing item string \"{evo[1]}\"")
                exit(-1)

            conditions["pokemon.evolve.useItem"].string = item
            conditions["pokemon.evolve.time"].string = "timeOfDay.night"
        elif evo[0] == "EVO_ITEM_HOLD_DAY":
            item = get_item_string(evo[1].removeprefix("ITEM_"))
            if item is None:
                print(f"\tERROR: Missing item string \"{evo[1]}\"")
                exit(-1)

            level_up = conditions["pokemon.evolve.levelUp"].nested
            level_up["pokemon.evolve.holdItem"].string = item
            level_up["pokemon.evolve.time"].string = "timeOfDay.day"
        elif evo[0] == "EVO_ITEM_DAY":
            item = get_item_string(evo[1].removeprefix("ITEM_"))
            if item is None:
                print(f"\tERROR: Missing item string \"{evo[1]}\"")
                exit(-1)

            conditions["pokemon.evolve.useItem"].string = item
            conditions["pokemon.evolve.time"].string = "timeOfDay.day"
        elif evo[0] == "EVO_SPECIFIC_MON_IN_PARTY":
            party_target = _stats[evo[1]]

            conditions[
                "pokemon.evolve.presentInParty"].string = party_target.name
        elif evo[0] == "EVO_MOVE_TYPE":
            level_up = conditions["pokemon.evolve.levelUp"].nested
            level_up[
                "pokemon.evolve.knowMoveType"].string = f"pokemon.type.{evo[1].removeprefix("TYPE_").lower()}"
        elif evo[0] == "EVO_SPECIFIC_MAP":
            continue
        else:
            print(f"\tERROR: Missing evo type \"{evo[0]}\"")
            exit(-1)

        if not append:
            base_entry.evolutions.append(evo_data)
            evo_index += 1


def generate(version: RogueVersion):
    print("Generating Pokedex")

    translations.add_translation("EmeraldRogue.Evolve.hasNature",
                                 "${value} nature")

    sprite_dir = directories.get_output_dir("emerald_rogue/assets/pokemon")

    for dexId in collections.OrderedDict(sorted(_dex_ids.items())):
        game_id = _dex_ids[dexId]
        species = game_id
        species_id = game_id

        forms = _species_forms[species]
        first_form_key = next(iter(_species_forms[species]))
        first_form_key = None if first_form_key == "_" else first_form_key

        if not _stats.__contains__(
                f"{species_id}{("" if first_form_key is None else f"_{first_form_key}")}"):
            if first_form_key is None:
                first_form_key = "NORMAL"

        first_form: pb_pokedex.Species = _stats[
            f"{species_id}{("" if first_form_key is None else f"_{first_form_key}")}"]

        for form in forms:
            form = None if form == "_" else form

            if form == "EMARK":
                form = "EXCLAMATION"
            elif form == "QMARK":
                form = "QUESTION"
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
                elif form == "ALOLAN":
                    form = "ALOLA"
                elif form == "GALARIAN":
                    form = "GALAR"
                elif form == "HISUIAN":
                    form = "HISUI"
                elif form == "PALDEAN":
                    form = "PALDEA"
                elif species == "FLABEBE" or species == "FLOETTE" or species == "FLORGES":
                    form = form.removesuffix("_FLOWER")
            else:
                if species == "UNOWN":
                    form = "A"

            stats.id = dexId

            file_form_id = f"{game_strings.clean_up(species_id)}{"" if form is None else f"-{game_strings.clean_up(form)}"}"
            file_id = f"{game_strings.clean_up(species_id)}"

            if os.path.isfile(
                    os.path.join(sprite_dir, "party", f"{file_form_id}.gif")):
                stats.sprites.party = f"pokelink-community:/emerald_rogue/assets/pokemon/party/{file_form_id}.gif"
            elif os.path.isfile(os.path.join(sprite_dir, "shiny",
                                             f"{file_id}-gmax.gif")) and species != "EEVEE":
                stats.sprites.normal = f"pokelink-community:/emerald_rogue/assets/pokemon/party/{file_id}-gmax.gif"
            elif os.path.isfile(
                    os.path.join(sprite_dir, "party", f"{file_id}.gif")):
                stats.sprites.party = f"pokelink-community:/emerald_rogue/assets/pokemon/party/{file_id}.gif"
            else:
                print(
                    f"\tWARNING: Not able to find a party sprite for {file_form_id}")

            if os.path.isfile(
                    os.path.join(sprite_dir, "normal", f"{file_form_id}.png")):
                stats.sprites.normal = f"pokelink-community:/emerald_rogue/assets/pokemon/normal/{file_form_id}.png"
            elif os.path.isfile(os.path.join(sprite_dir, "normal",
                                             f"{file_id}-gmax.png")) and species != "EEVEE":
                stats.sprites.normal = f"pokelink-community:/emerald_rogue/assets/pokemon/normal/{file_id}-gmax.png"
            elif os.path.isfile(
                    os.path.join(sprite_dir, "normal", f"{file_id}.png")):
                stats.sprites.normal = f"pokelink-community:/emerald_rogue/assets/pokemon/normal/{file_id}.png"
            else:
                print(
                    f"\tWARNING: Not able to find a normal sprite for {file_form_id}")

            if os.path.isfile(
                    os.path.join(sprite_dir, "shiny", f"{file_form_id}.png")):
                stats.sprites.shiny = f"pokelink-community:/emerald_rogue/assets/pokemon/shiny/{file_form_id}.png"
            elif os.path.isfile(os.path.join(sprite_dir, "shiny",
                                             f"{file_id}-gmax.png")) and species != "EEVEE":
                stats.sprites.shiny = f"pokelink-community:/emerald_rogue/assets/pokemon/shiny/{file_id}-gmax.png"
            elif os.path.isfile(
                    os.path.join(sprite_dir, "shiny", f"{file_id}.png")):
                stats.sprites.shiny = f"pokelink-community:/emerald_rogue/assets/pokemon/shiny/{file_id}.png"
            else:
                print(
                    f"\tWARNING: Not able to find a shiny sprite for {file_form_id}")

            if os.path.isfile(os.path.join(sprite_dir, "normal",
                                           f"{file_form_id}-f.png")) and stats.genderRatio != 0 and stats.genderRatio != 255:
                stats.sprites.female = f"pokelink-community:/emerald_rogue/assets/pokemon/normal/{file_form_id}-f.png"

            if os.path.isfile(os.path.join(sprite_dir, "shiny",
                                           f"{file_form_id}-f.png")) and stats.genderRatio != 0 and stats.genderRatio != 255:
                stats.sprites.femaleShiny = f"pokelink-community:/emerald_rogue/assets/pokemon/shiny/{file_form_id}-f.png"

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
                        f"EmeraldRogue.Form.{game_strings.clean_up(form_translation)}",
                        form_translation)
                    stats.formName = f"EmeraldRogue.Form.{game_strings.clean_up(form_translation)}"

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
        os.path.join(directories.get_output_dir(
            "emerald_rogue" + "/" + (
                "vanilla" if version == RogueVersion.VANILLA else "expansion"),
            True),
            "emeraldRogue.dex"), json_format.MessageToDict(_dex))
