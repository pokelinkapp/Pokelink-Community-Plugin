from emerald_rogue._version import RogueVersion
from pokelink import translations, directories
import emerald_rogue._abilities as abilities
import emerald_rogue._exp_data as exp_data
import emerald_rogue._items as items
import emerald_rogue._moves as moves
import emerald_rogue._pokedex as pokedex
import emerald_rogue._sprites as sprites

def _process(version: RogueVersion):
    sprites.process()
    abilities.process(version)
    items.process(version)
    moves.process(version)
    pokedex.process(version)

def _generate(version: RogueVersion):
    abilities.generate(version)
    exp_data.generate(version)
    items.generate(version)
    moves.generate(version)
    pokedex.generate(version)


def generate():
    translations.clear()
    print("Generating Emerald Rogue Vanilla")
    _process(RogueVersion.VANILLA)
    _generate(RogueVersion.VANILLA)
    print()
    print ("Generating Emerald Rogue Expansion")
    _process(RogueVersion.EXPANSION)
    _generate(RogueVersion.EXPANSION)

    translations.write_translations(directories.get_output_dir("emerald_rogue/translations", True))
