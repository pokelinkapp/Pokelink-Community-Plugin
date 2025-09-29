import emerald_imperium.data._species_form_data as species_form_data
import emerald_imperium.data._exp_data as exp_data
import emerald_imperium.data._abilities as abilities
import emerald_imperium.data._items as items
import emerald_imperium.data._pokedex as pokedex

def process():
    species_form_data.process()
    abilities.process()
    items.process()
    pokedex.process()

def generate():
    exp_data.generate()
    abilities.generate()
    items.generate()
    pokedex.generate()
