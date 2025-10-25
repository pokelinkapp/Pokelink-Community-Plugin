import collections

from pygccxml import utils
from pygccxml import declarations
from pygccxml import parser

import pokelink.proto.v0_7_1.pokedex_pb2 as pb_pokedex
import pokelink.directories as directories
import pokelink.translations as translations
from google.protobuf import json_format

from emerald_rogue import RogueVersion
from pokelink import strip_comments, game_strings, core_plugin
from pokelink.gen3 import poke_math
from pokelink.json_output import write_file

import os

_dex = pb_pokedex.Pokedex()

_dex.version = "0.7.1"

_species_form_id = dict()
_species_forms = dict()
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
                    species) and species != "NIDORAN_F" and species != "NIDORAN_M" and species != "TYPE_NULL":
                split = species.split("_")
                mon = split[0]
                form = str.join("_", split[1:])

                if not _species_forms.__contains__(mon):
                    _species_forms[mon] = dict()
                    _species_forms[mon][form] = 0
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
                    def_args = brackets[1].removesuffix(")").replace(" ", "").split(",")
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

                        args = split[1].removeprefix("(").removesuffix("),").replace(" ", "").split(",")

                        replace_args, replacement = _def_replacements_args[replace]

                        for i in range(args.__len__()):
                            replacement = replacement.replace(f" ##{replace_args[i]}", f" {args[i]}")
                            replacement = replacement.replace(f" #{replace_args[i]}", f" {args[i]}")
                            replacement = replacement.replace(f" {replace_args[i]}", f" {args[i]}")

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
                                f" ##{replace_args[i]}", f" {args[i]}")
                            replacement = replacement.replace(
                                f" #{replace_args[i]}", f" {args[i]}")
                            replacement = replacement.replace(
                                f" {replace_args[i]}", f" {args[i]}")

                        line_clean = f"{replacement},\n"

                param_lines += f"{line_clean}\n"

            temp_lines = param_lines

            for replace in _def_replacements:
                temp_lines = temp_lines.replace(replace, _def_replacements[replace])

        lines = temp_lines.split("\n")

    reading = False
    current_pokemon: pb_pokedex.Species | None = None
    current_name: str | None = None

    for line in lines:
        line = line.strip()
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
            elif line.startswith(".type1"):
                type = line.removeprefix(".type1 = ").removesuffix(",")
                current_pokemon.types.insert(0, f"pokemon.type.{type.lower().removeprefix("type_")}")
            elif line.startswith(".type2"):
                type = line.removeprefix(".type2 = ").removesuffix(",")
                current_pokemon.types.append(f"pokemon.type.{type.lower().removeprefix("type_")}")
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


def generate(version: RogueVersion):
    print("Generating Pokedex")

    sprite_dir = directories.get_output_dir("emerald_rogue/assets/pokemon")

    for dexId in collections.OrderedDict(sorted(_dex_ids.items())):
        game_id = _dex_ids[dexId]
        species = game_id
        species_id = game_id

        forms = _species_forms[species]
        first_form_key = next(iter(_species_forms[species]))
        first_form_key = None if first_form_key == "_" else first_form_key

        if not _stats.__contains__(f"{species_id}{("" if first_form_key is None else f"_{first_form_key}")}"):
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
            else:
                if species == "UNOWN":
                    form = "A"

            stats.id = dexId

            file_form_id = f"{game_strings.clean_up(species_id)}{"" if form_id is None else f"-{game_strings.clean_up(form_id)}"}"
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
                stats.ClearField("id")
                first_form.forms.append(stats)
        _dex.entries.append(first_form)

    write_file(
        os.path.join(directories.get_output_dir(
            "emerald_rogue" + "/" + (
                "vanilla" if version == RogueVersion.VANILLA else "expansion"),
            True),
            "emeraldRogue.dex"), json_format.MessageToDict(_dex))
