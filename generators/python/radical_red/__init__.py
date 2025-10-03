import pokelink.directories as directories
import pokelink.translations as translations

import radical_red._types
import radical_red._abilities
import radical_red._items
import radical_red._moves
import radical_red._pokedex

def generate():
    translations.clear()
    print("Generating Radical Red")
    _types.process()
    _abilities.generate()
    _items.generate()
    _moves.generate()
    _pokedex.generate()

    translations.write_translations(directories.get_output_dir("radred/translations", True))