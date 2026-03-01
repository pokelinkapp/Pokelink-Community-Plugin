import pokelink.directories as directories
import pokelink.translations as translations

import pokemon_null._exp_data as exp_data
import pokemon_null._abilities as abilities
import pokemon_null._items as items
import pokemon_null._pokedex as pokedex
import pokemon_null._sprites as sprites
import pokemon_null._moves as moves

def _process():
    sprites.process()
    abilities.process()
    items.process()
    moves.process()
    pokedex.process()

def generate():
    translations.clear()
    print("Generating Pokemon Null")
    _process()
    exp_data.generate()
    abilities.generate()
    items.generate()
    moves.generate()
    pokedex.generate()

    translations.write_translations(directories.get_output_dir("pokemon_null/translations", True))