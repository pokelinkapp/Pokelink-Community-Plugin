import os.path

import emerald_rogue
import pokelink.directories
import runAndBun
import emerald_imperium
import radical_red
import pokemon_null

import locale
locale.setlocale(locale.LC_ALL, '')

runAndBun.generate()
print()
emerald_imperium.generate()
print()
radical_red.generate()
print()
emerald_rogue.generate()
if os.path.isdir(os.path.join(pokelink.directories.get_external_dir("private"), "pokemon_null")):
    print()
    pokemon_null.generate()