import pokelink.directories as directories
import pokelink.translations as translations

import pokemon_unknown._abilities as _abilities
import pokemon_unknown._exp as _exp
import pokemon_unknown._items as _items
import pokemon_unknown._moves as _moves
import pokemon_unknown._pokedex as _pokedex


def generate():
    translations.clear()
    print("Generating Pokemon Unknown")
    _abilities.process()
    _exp.process()
    _items.process()
    _moves.process()
    _pokedex.process()
    _abilities.generate()
    _exp.generate()
    _items.generate()
    _moves.generate()
    _pokedex.generate()

    translations.write_translations(directories.get_output_dir("pokemon-unknown/translations", True))
