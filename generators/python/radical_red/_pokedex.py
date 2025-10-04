from typing import List, Literal

import pokelink.directories as directories
import pokelink.proto.v0_7_1.pokedex_pb2 as pb_pokedex
from google.protobuf import json_format
from radical_red._items import items
from radical_red._moves import moves
from radical_red._types import types
from radical_red._abilities import abilities, ability_ids

import json
import os

from pokelink import game_strings, translations
from pokelink.json_output import write_file

_dex_data: List[pb_pokedex.Species] = []

_game_id_dex_data = {}

_out_dex = pb_pokedex.Pokedex()

def _toxtricity_evo(evo_from: pb_pokedex.Species, evo: List,
                    natures: List[str]) -> pb_pokedex.Evolution:
    value = pb_pokedex.Evolution()
    to = _game_id_dex_data[evo[2]]

    value.to = to.id
    value.toForm = to.form
    value.fromForm = evo_from.form

    value.conditions["pokemon.evolve.level"].number = evo[1]

    value.conditions["pokemon.evolve.nature"].stringArray.extend(natures)

    return value


def _rockruff_evo(evo_from: pb_pokedex.Species,
                  evo: List) -> pb_pokedex.Evolution:
    value = pb_pokedex.Evolution()
    to = _game_id_dex_data[evo[2]]

    value.to = to.id
    value.toForm = to.form
    value.fromForm = evo_from.form

    value.conditions["pokemon.evolve.level"].number = evo[1]

    if evo[3] == 1041:
        value.conditions["pokemon.evolve.time"].string = "timeOfDay.day"
    elif evo[3] == 5144:
        value.conditions["pokemon.evolve.time"].string = "timeOfDay.night"
    else:
        value.conditions["pokemon.evolve.time"].string = "timeOfDay.dusk"

    return value


def _level_with_pokemon_evo(evo_from: pb_pokedex.Species,
                            evo: List) -> pb_pokedex.Evolution:
    value = pb_pokedex.Evolution()
    to = _game_id_dex_data[evo[2]]

    value.to = to.id
    value.toForm = to.form
    value.fromForm = evo_from.form

    value.conditions["pokemon.evolve.levelUp"].nested[
        "pokemon.evolve.presentInParty"].string = _game_id_dex_data[evo[1]].name

    return value


def _level_with_move_evo(evo_from: pb_pokedex.Species,
                         evo: List) -> pb_pokedex.Evolution:
    value = pb_pokedex.Evolution()
    to = _game_id_dex_data[evo[2]]

    value.to = to.id
    value.toForm = to.form
    value.fromForm = evo_from.form

    value.conditions["pokemon.evolve.levelUp"].nested[
        "pokemon.evolve.knowMove"].string = moves[evo[1] - 1]["name"]

    return value


def _level_extra_condition_evo(evo_from: pb_pokedex.Species, evo: List,
                               condition: Literal[
                                   "male", "female", "night", "day"]) -> pb_pokedex.Evolution:
    value = pb_pokedex.Evolution()
    to = _game_id_dex_data[evo[2]]

    value.to = to.id
    value.toForm = to.form
    value.fromForm = evo_from.form

    value.conditions["pokemon.evolve.level"].number = evo[1]

    if condition == "male" or condition == "female":
        value.conditions["pokemon.evolve.gender"].string = "Gender." + condition
    elif condition == "day" or condition == "night":
        value.conditions[
            "pokemon.evolve.time"].string = f"timeOfDay.{condition}"

    return value


def _level_with_type_pokemon_evo(evo_from: pb_pokedex.Species,
                                 evo: List) -> pb_pokedex.Evolution:
    value = pb_pokedex.Evolution()
    to = _game_id_dex_data[evo[2]]

    value.to = to.id
    value.toForm = to.form
    value.fromForm = evo_from.form

    value.conditions["pokemon.evolve.level"].number = evo[1]
    value.conditions[
        "pokemon.evolve.typedPokemonPresentInParty"].string = f"pokemon.type.{game_strings.clean_up(types[str(evo[3])])}"

    return value


def _level_friendship_move_type_evo(evo_from: pb_pokedex.Species,
                                    evo: List) -> pb_pokedex.Evolution:
    value = pb_pokedex.Evolution()
    to = _game_id_dex_data[evo[2]]

    value.to = to.id
    value.toForm = to.form
    value.fromForm = evo_from.form

    condition = pb_pokedex.EvolutionCondition()
    condition.nested[
        "pokemon.evolve.knowMoveType"].string = f"pokemon.type.{game_strings.clean_up(types[str(evo[1])])}"
    condition.nested["pokemon.evolve.friendship"].string = "friendship.high"

    value.conditions["pokemon.evolve.levelUp"].CopyFrom(condition)

    return value


def _level_rain_evo(evo_from: pb_pokedex.Species,
                    evo: List) -> pb_pokedex.Evolution:
    value = pb_pokedex.Evolution()
    to = _game_id_dex_data[evo[2]]

    value.to = to.id
    value.toForm = to.form
    value.fromForm = evo_from.form

    value.conditions["pokemon.evolve.level"].number = evo[1]
    value.conditions["pokemon.evolve.weather"].string = "weather.raining"

    return value


def _shedinja_evo(evo_from: pb_pokedex.Species,
                  evo: List) -> pb_pokedex.Evolution:
    value = pb_pokedex.Evolution()
    to = _game_id_dex_data[evo[2]]

    value.to = to.id
    value.toForm = to.form
    value.fromForm = evo_from.form

    value.conditions["pokemon.evolve.level"].number = 20
    value.conditions["pokemon.evolve.emptySlot"].nested[
        "pokemon.evolve.hasItem"].string = "pokemon.ball.poke_ball"

    return value


def _level_with_percentage_evo(evo_from: pb_pokedex.Species,
                               evo: List) -> pb_pokedex.Evolution:
    value = pb_pokedex.Evolution()
    to = _game_id_dex_data[evo[2]]

    value.to = to.id
    value.toForm = to.form
    value.fromForm = evo_from.form

    value.conditions["pokemon.evolve.level"].number = evo[1]
    value.conditions["pokemon.evolve.rarity"].string = "rarity.p50Chance"

    return value


def _level_stats_evo(evo_from: pb_pokedex.Species, evo: list, kind: Literal[
    "atk>def", "atk<def", "atk=def"]) -> pb_pokedex.Evolution:
    value = pb_pokedex.Evolution()

    to = _game_id_dex_data[evo[2]]

    value.to = to.id
    value.toForm = to.form
    value.fromForm = evo_from.form

    value.conditions["pokemon.evolve.level"].number = evo[1]
    value.conditions[
        "pokemon.evolve.stat"].string = f"stat.{"attack>defense" if kind == "atk>def" else "attack<defense" if kind == "atk<def" else "attack=defense"}"

    return value


def _use_item_evo(evo_from: pb_pokedex.Species,
                  evo: List) -> pb_pokedex.Evolution:
    value = pb_pokedex.Evolution()

    to = _game_id_dex_data[evo[2]]

    value.to = to.id
    value.toForm = to.form
    value.fromForm = evo_from.form

    value.conditions["pokemon.evolve.useItem"].string = f"{items[evo[1] - 1]}"
    if evo[1] == 101:
        value.conditions[
            "pokemon.evolve.gender"].string = f"Gender.{"female" if evo[3] == 254 else "male"}"

    return value


def _friendship_evo(evo_from: pb_pokedex.Species,
                    evo: List, time_of_day: Literal[
                                                "day", "night"] | None = None) -> pb_pokedex.Evolution:
    value = pb_pokedex.Evolution()

    to = _game_id_dex_data[evo[2]]

    value.to = to.id
    value.toForm = to.form
    value.fromForm = evo_from.form

    condition = pb_pokedex.EvolutionCondition()
    if time_of_day is not None:
        condition.nested[
            "pokemon.evolve.time"].string = f"timeOfDay.{time_of_day}"
    condition.nested["pokemon.evolve.friendship"].string = "friendship.high"
    value.conditions["pokemon.evolve.levelUp"].CopyFrom(condition)

    return value


def _level_up_evo(evo_from: pb_pokedex.Species,
                  evo: List) -> pb_pokedex.Evolution:
    value = pb_pokedex.Evolution()

    to = _game_id_dex_data[evo[2]]

    value.to = to.id
    value.toForm = to.form
    value.fromForm = evo_from.form

    value.conditions["pokemon.evolve.level"].number = evo[1]

    return value


def _process_evo(entry: pb_pokedex.Species, target: pb_pokedex.Species,
                 species: dict):
    if not species.__contains__("evolutions"):
        return

    if not isinstance(species["evolutions"], list):
        return

    for evo in species["evolutions"]:
        if not isinstance(evo, list):
            continue

        type = evo[0]

        result: pb_pokedex.Evolution | None = None

        if 1 <= type <= 3:
            result = _friendship_evo(target, evo,
                                     None if type == 1 else "day" if type == 2 else "night")
        elif type == 4 or type == 13:
            result = _level_up_evo(target, evo)
        elif type == 7:
            result = _use_item_evo(target, evo)
        elif 8 <= type <= 10:
            result = _level_stats_evo(target, evo,
                                      "atk>def" if type == 8 else "atk=def" if type == 9 else "atk<def")
        elif type == 11 or type == 12:
            result = _level_with_percentage_evo(target, evo)
        elif type == 14:
            result = _shedinja_evo(target, evo)
        elif type == 16:
            result = _level_rain_evo(target, evo)
        elif type == 17:
            result = _level_friendship_move_type_evo(target, evo)
        elif type == 18:
            result = _level_with_type_pokemon_evo(target, evo)
        elif 20 <= type <= 23:
            result = _level_extra_condition_evo(target, evo,
                                                "male" if type == 20 else "female" if type == 21 else "night" if type == 22 else "day")
        elif type == 26:
            result = _level_with_move_evo(target, evo)
        elif type == 27:
            result = _level_with_pokemon_evo(target, evo)
        elif type == 28:
            result = _rockruff_evo(target, evo)
        elif 30 <= type <= 31:
            result = _toxtricity_evo(target, evo, [
                "pokemon.nature.brave", "pokemon.nature.adamant",
                "pokemon.nature.naughty", "pokemon.nature.docile",
                "pokemon.nature.impish", "pokemon.nature.lax",
                "pokemon.nature.hasty", "pokemon.nature.jolly",
                "pokemon.nature.naive", "pokemon.nature.rash",
                "pokemon.nature.sassy", "pokemon.nature.quirky"
            ] if type == 30 else [
                "pokemon.nature.lonely", "pokemon.nature.bold",
                "pokemon.nature.relaxed", "pokemon.nature.timid",
                "pokemon.nature.timid", "pokemon.nature.serious",
                "pokemon.nature.modest", "pokemon.nature.mild",
                "pokemon.nature.quiet", "pokemon.nature.bashful",
                "pokemon.nature.calm", "pokemon.nature.calm",
                "pokemon.nature.gentle", "pokemon.nature.careful"
            ])
        elif type == 254 and evo[3] == 2:
            result = _level_with_move_evo(target, evo)


        if result is not None:
            entry.evolutions.append(result)

def _clean_up_types(entry: pb_pokedex.Species):
    for index in range(entry.types.__len__()):
        entry.types[index] = f"pokemon.type.{game_strings.clean_up(entry.types[index])}"

def _clean_up_abilities(entry: pb_pokedex.Species):
    for index in range(entry.abilities.__len__()):
        if entry.abilities[index] == "":
            continue

        c_c_id = game_strings.clean_up(entry.abilities[index]).replace("_", "")

        found = False

        for a_idx in range(ability_ids.__len__()):
            a_id = ability_ids[a_idx]
            c_a_id = game_strings.clean_up(a_id).replace("_", "")

            if c_c_id == c_a_id:
                found = True
                entry.abilities[index] = abilities[a_idx]
                break

        if not found:
            print(f"\tWARNING: Unable to identify ability {entry.abilities[index]}")


def _clean_up_form(entry: pb_pokedex.Species):
    if not entry.HasField("formName"):
        return

    if not game_strings.has_form(entry.formName) and not entry.name.endswith("unown") and not entry.formName == "GALAR_ZEN" and entry.id != 128:
        print(f"\tWARNING: Missing pokelink form {entry.formName}")

        name = entry.formName
        first = True

        for part in name.split("_"):
            if first:
                first = False
                name = part[0] + part[1:].lower()
                continue

            name += " " + part[0] + part[1:].lower()

        translations.add_translation(
            f"RadicalRed.Form.{game_strings.clean_up(entry.formName)}", name)
        entry.formName = f"RadicalRed.Form.{game_strings.clean_up(entry.formName)}"
    else:
        entry.formName = f"pokemon.form.{game_strings.clean_up(entry.formName)}"

    

def generate():
    print("Generating Pokedex")
    _out_dex.version = "0.7.1"

    species_data: dict | None = None

    with open(os.path.join(directories.get_external_dir("rad-red-json"),
                           "species.json")) as data:
        species_data = json.load(data)

    with open(os.path.join(directories.get_external_dir("rad-red-json"),
                           "dex.json")) as data:
        for entry in json.load(data):
            _dex_data.append(json_format.ParseDict(entry, pb_pokedex.Species()))

    for entry in _dex_data:
        _game_id_dex_data[entry.gameId] = entry
        entry.sprites.party = f"pokelink-community:/radred/assets/sprites/party/{entry.id}.gif"
        entry.sprites.normal = entry.sprites.shiny = f"pokelink-community:/radred/assets/sprites/normal/{entry.id}.png"

        if not game_strings.has_species(entry.name) and entry.id != 29 and entry.id != 32:
            entry.name = entry.name.split("_")[0]

        if not game_strings.has_species(entry.name) and entry.id != 29 and entry.id != 32:
            translations.add_translation(
            f"RadicalRed.Species.{game_strings.clean_up(entry.name)}", entry.name[0] + entry.name[1:].lower())
            entry.name = f"RadicalRed.Species.{game_strings.clean_up(entry.name)}"
        else:
            entry.name = f"pokemon.species.{game_strings.clean_up(entry.name)}"

        _clean_up_types(entry)
        _clean_up_abilities(entry)
        _clean_up_form(entry)

        for form in entry.forms:
            form.name = entry.name
            form.sprites.party = f"pokelink-community:/radred/assets/sprites/party/{entry.id}-{form.form}.gif"
            form.sprites.normal = form.sprites.shiny = f"pokelink-community:/radred/assets/sprites/normal/{entry.id}.{form.form}.png"

            _clean_up_types(form)
            _clean_up_abilities(form)
            form.id = entry.id
            _clean_up_form(form)
            form.ClearField("id")

            temp_form = pb_pokedex.Species()
            temp_form.CopyFrom(form)
            temp_form.id = entry.id
            _game_id_dex_data[form.gameId] = temp_form

    for entry in _dex_data:
        _process_evo(entry, entry, species_data[str(entry.gameId)])
        for form in entry.forms:
            if species_data.__contains__(str(form.gameId)):
                _process_evo(entry, form, species_data[str(form.gameId)])

    for entry in _dex_data:
        _out_dex.entries.append(entry)

    write_file(
        os.path.join(directories.get_output_dir("radred/v4.1", True),
                     "radred.dex"), json_format.MessageToDict(_out_dex))
