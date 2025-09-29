import emerald_imperium.data
import pokelink.directories as directories
import pokelink.translations as translations


def generate():
    translations.clear()
    print("Generating Emerald Imperium")
    emerald_imperium.data.process()
    emerald_imperium.data.generate()

    translations.write_translations(directories.get_output_dir("emerald_imperium/translations/py", True))