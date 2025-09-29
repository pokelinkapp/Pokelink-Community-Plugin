import runAndBun._pokedex
import runAndBun._items
import pokelink.directories as directories
import pokelink.translations as translations


def generate():
    translations.clear()
    print("Generating Run and Bun files")
    runAndBun._items.generate_items()
    runAndBun._pokedex.generate_abilities()
    runAndBun._pokedex.generate_dex()

    translations.write_translations(directories.get_output_dir("runAndBun/translations/", True))