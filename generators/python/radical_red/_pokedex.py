from typing import List

import pokelink.directories as directories
import pokelink.proto.v0_7_1.pokedex_pb2 as pb_pokedex
from google.protobuf import json_format

import json
import os

from pokelink import game_strings, translations
from pokelink.json_output import write_file

_dex_data: List[pb_pokedex.Species] = []

_game_id_dex_data = {}

_out_dex = pb_pokedex.Pokedex()

skip_evos = []

def _level_up_evo(evo_from: pb_pokedex.Species, evo: List) -> pb_pokedex.Evolution:
    value = pb_pokedex.Evolution()

    to_id = evo[2]

    to = _game_id_dex_data[to_id]

    value.to = to.id
    value.toForm = to.form
    value.fromForm = evo_from.form

    condition = pb_pokedex.EvolutionCondition()
    condition.number = evo[1]
    value.conditions["pokemon.evolve.level"].CopyFrom(condition)

    return value

def _process_evo(entry: pb_pokedex.Species, target: pb_pokedex.Species, species: dict):
    if skip_evos.__contains__(entry.id):
        return

    if not species.__contains__("evolutions"):
        return

    if not isinstance(species["evolutions"], list):
        return

    for evo in species["evolutions"]:
        if not isinstance(evo, list):
            continue

        type = evo[0]

        result: pb_pokedex.Evolution | None = None

        if type == 4 or type == 13:
            result = _level_up_evo(target, evo)

        if result is not None:
            if not skip_evos.__contains__(result.to):
                skip_evos.append(result.to)

            entry.evolutions.append(result)




def generate():
    print("Generating Pokedex")
    _out_dex.version = "0.7.1"

    species_data: dict | None = None

    with open(os.path.join(directories.get_external_dir("rad-red-json"),
                           "species.json")) as data:
        species_data = json.load(data)

    with open(os.path.join(directories.get_external_dir("rad-red-json"), "dex.json")) as data:
        for entry in json.load(data):
            _dex_data.append(json_format.ParseDict(entry, pb_pokedex.Species()))

    for entry in _dex_data:
        _game_id_dex_data[entry.gameId] = entry
        entry.sprites.party = f"pokelink-community:/radred/assets/sprites/party/{entry.id}.gif"
        entry.sprites.normal = entry.sprites.shiny = f"pokelink-community:/radred/assets/sprites/normal/{entry.id}.png"
        for form in entry.forms:
            form.sprites.party = f"pokelink-community:/radred/assets/sprites/party/{entry.id}-{form.form}.gif"
            form.sprites.normal = form.sprites.shiny = f"pokelink-community:/radred/assets/sprites/normal/{entry.id}.{form.form}.png"
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