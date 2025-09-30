import os
import pokelink.directories as directories
from PIL import Image

def _process_item_sprites(item_dir: str):
    print("\tProcessing Item Sprites")
    output = directories.get_output_dir("emerald_imperium/assets/items", True)
    icons = os.path.join(item_dir, "icons")
    palettes = os.path.join(item_dir, "icon_palettes")

    for file in os.listdir(icons):
        name, ext = os.path.splitext(file)

        if not os.path.isfile(os.path.join(palettes, f"{name}.pal")):
            continue


        item_palette = []
        with open(os.path.join(palettes, f"{name}.pal"), "r") as palette_file:
            for line in [clean.strip() for clean in palette_file]:
                sections = line.split(" ")

                if sections.__len__() < 3:
                    continue

                item_palette += [int(sections[0]), int(sections[1]), int(sections[2]), 0 if item_palette.__len__() == 0 else 255 ]

        with Image.open(os.path.join(icons, f"{name}{ext}")) as sprite:
            new_sprite = Image.new("P", sprite.size)
            new_sprite.putpalette(item_palette, rawmode="RGBA")
            new_sprite.paste(sprite, (0,0) + sprite.size)
            if new_sprite.size < (48, 48):
                new_sprite = new_sprite.resize((48, 48))
            new_sprite.save(os.path.join(output, name + ".png"))


    print(f"\t\t {os.listdir(icons).__len__():n} item icons generated")

def _process_pokemon_sprites(pokemon_dir: str):
    print("\tProcessing Pokemon Sprites")
    output = directories.get_output_dir("emerald_imperium/assets/pokemon", True)

def process():
    print("Processing Sprites")
    root_dir = os.path.join(directories.get_external_dir("emerald-imperium"), "graphics")
    _process_item_sprites(os.path.join(root_dir, "items"))
    _process_pokemon_sprites(os.path.join(root_dir, "pokemon"))