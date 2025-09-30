import pokelink.directories as directories
import pokelink.translations as translations

import emerald_imperium._exp_data as exp_data
import emerald_imperium._abilities as abilities
import emerald_imperium._items as items
import emerald_imperium._pokedex as pokedex

def _process():
    abilities.process()
    items.process()
    pokedex.process()


def generate():
    translations.clear()
    print("Generating Emerald Imperium")
    _process()
    exp_data.generate()
    abilities.generate()
    items.generate()
    pokedex.generate()

    translations.write_translations(directories.get_output_dir("emerald_imperium/translations/py", True))