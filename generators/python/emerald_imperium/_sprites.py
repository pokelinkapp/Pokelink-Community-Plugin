import os
from pickletools import optimize

import pokelink.directories as directories
from pokelink import game_strings
from PIL import Image

from pokelink.gen3 import gba_image

_valid_names = [
    "anim_front.png",
    "front.png",
    "icon.png",
    # female sprites
    "anim_frontf.png",
    "frontf.png",
    "iconf.png"
]

_sprite_count = 0


def _process_item_sprites(item_dir: str):
    print("\tProcessing Item Sprites")
    output = directories.get_output_dir("emerald_imperium/assets/items", True)
    icons = os.path.join(item_dir, "icons")
    palettes = os.path.join(item_dir, "icon_palettes")

    for file in os.scandir(icons):
        name, ext = os.path.splitext(file.name)

        if not os.path.isfile(os.path.join(palettes, f"{name}.pal")):
            continue

        new_sprite = gba_image.swap_palette(os.path.join(icons, f"{name}{ext}"),
                                            os.path.join(palettes,
                                                         f"{name}.pal"))

        if new_sprite.size < (64, 64):
            new_sprite = new_sprite.resize((64, 64))
        new_sprite.save(os.path.join(output, name + ".png"))

    print(f"\t\t {os.listdir(icons).__len__():n} item icons generated")


def _process_pokemon_sprite_images(sprite_dir: os.DirEntry, output_name: str,
                                   output_dir: str):
    if (output_name == "egg"
            or output_name == "question_mark"
            or output_name == "icon_palettes"
            or output_name == "basculin-hisui"
            or output_name == "spinda-spots"
            or output_name == "rotom-normal"):
        return

    global _sprite_count
    sprite_made = False
    shiny_sprite_made = False
    party_sprite_made = False

    for sprite in _valid_names:
        target_sprite = sprite
        is_female_sprite = _valid_names.index(sprite) > 2
        is_icon = sprite.startswith("icon")

        if not is_icon and not is_female_sprite:
            if output_name == "dusknoir-mega":
                target_sprite = "megadusknoir.png"
            elif output_name == "roserade-mega":
                target_sprite = "megaroserade.png"
            elif output_name == "empoleon-mega_d":
                target_sprite = "megaempoleond.png"
            elif output_name == "empoleon-mega_o":
                target_sprite = "megaempoleono.png"
            elif output_name == "torterra-mega":
                target_sprite = "megatorterra.png"
            elif output_name == "infernape-mega":
                target_sprite = "megainfernape.png"
            elif output_name == "luxray-mega":
                target_sprite = "megaluxray.png"
            elif output_name == "slaking-mega":
                target_sprite = "megaslaking.png"

        if not os.path.isfile(os.path.join(sprite_dir.path, target_sprite)):
            if os.path.isfile(
                    os.path.join(sprite_dir.path, "..", target_sprite)):
                if is_icon:
                    if output_name == "alcremie-strawberry_vanilla_cream":
                        target_sprite = "../" + sprite
                    else:
                        party_sprite_made = True
                        continue
                else:
                    if (output_name.startswith("silvally-")
                            or output_name.startswith("arceus-")
                            or output_name.startswith("florges-")
                            or output_name.startswith("floette-")
                            or output_name.startswith("flabebe-")
                            or output_name.startswith("squawkabilly-")
                            or output_name.startswith("genesect-")
                            or output_name.startswith("deerling-")
                            or output_name.startswith("pikachu-")
                            or output_name.startswith("eevee-")
                            or output_name.startswith("minior-core_")):
                        if is_female_sprite and not os.path.isfile(
                                os.path.join(sprite_dir.path, target_sprite)):
                            continue
                        target_sprite = "../" + sprite
                    else:
                        continue
            else:
                continue

        target_palette = os.path.join(sprite_dir.path, "normal.pal")

        if not is_icon and not is_female_sprite:
            if output_name == "dusknoir-mega":
                target_palette = os.path.join(sprite_dir.path,
                                              "megadusknoir.pal")
            elif output_name == "roserade-mega":
                target_palette = os.path.join(sprite_dir.path,
                                              "megaroserade.pal")
            elif output_name == "empoleon-mega_d":
                target_palette = os.path.join(sprite_dir.path,
                                              "megadnormal.pal")
            elif output_name == "empoleon-mega_o":
                target_palette = os.path.join(sprite_dir.path,
                                              "megaonormal.pal")
            elif output_name == "torterra-mega":
                target_palette = os.path.join(sprite_dir.path,
                                              "megatorterra.pal")
            elif output_name == "infernape-mega":
                target_palette = os.path.join(sprite_dir.path,
                                              "megainfernapenormal.pal")
            elif output_name == "luxray-mega":
                target_palette = os.path.join(sprite_dir.path, "megaluxray.pal")
            elif output_name == "slaking-mega":
                target_palette = os.path.join(sprite_dir.path,
                                              "megaslaking.pal")
            elif output_name == "dialga-primal":
                target_palette = os.path.join(sprite_dir.path,
                                              "dialgaprimal.pal")
            elif output_name == "palkia-primal":
                target_palette = os.path.join(sprite_dir.path,
                                              "palkiaprimal.pal")
            elif output_name.startswith("alcremie-") and not output_name.endswith("gmax"):
                target_palette = os.path.join(sprite_dir.path, (output_name.removeprefix("alcremie-") if not output_name.endswith("vanilla_cream") else f"{sprite_dir.name}_default") + ".pal")

        if not os.path.isfile(target_palette):
            target_palette = os.path.join(sprite_dir.path, "..", "normal.pal")

        if not os.path.isfile(target_palette):
            continue

        if is_icon:
            new_sprite = gba_image.remove_icon_background(
                os.path.join(sprite_dir.path, target_sprite))
        else:
            new_sprite = gba_image.swap_palette(
                os.path.join(sprite_dir.path, target_sprite),
                target_palette)

        if new_sprite.width < new_sprite.height:
            if not is_icon:
                new_sprite = new_sprite.crop(
                    (0, 0, new_sprite.width, new_sprite.width))
            else:
                party_sprite_made = True
                new_sprite = new_sprite.resize((64, 128))
                new_sprite.crop(
                    (0, 0, new_sprite.width, new_sprite.width)).save(
                    os.path.join(output_dir, "party",
                                 f"{output_name if output_name != "alcremie-strawberry_vanilla_cream" else "alcremie"}{"-f" if is_female_sprite else ""}.gif"),
                    "GIF", transparency=0, disposal=2,
                    save_all=True, optimize=False, loop=0, duration=100,
                    append_images=[
                        new_sprite.crop(
                            (0, new_sprite.width,
                             new_sprite.height, new_sprite.height))
                    ])
                _sprite_count += 1
                continue

        new_sprite.save(os.path.join(output_dir, "normal",
                                     f"{output_name}{"-f" if is_female_sprite else ""}.png"))
        sprite_made = True
        _sprite_count += 1

        target_palette = os.path.join(sprite_dir.path, "shiny.pal")

        if not is_icon and not is_female_sprite:
            if output_name == "dusknoir-mega":
                target_palette = os.path.join(sprite_dir.path,
                                              "megadusknoir.pal")
            elif output_name == "roserade-mega":
                target_palette = os.path.join(sprite_dir.path,
                                              "megaroserade.pal")
            elif output_name == "empoleon-mega_d":
                target_palette = os.path.join(sprite_dir.path, "megadshiny.pal")
            elif output_name == "empoleon-mega_o":
                target_palette = os.path.join(sprite_dir.path, "megaoshiny.pal")
            elif output_name == "torterra-mega":
                target_palette = os.path.join(sprite_dir.path,
                                              "megatorterra.pal")
            elif output_name == "infernape-mega":
                target_palette = os.path.join(sprite_dir.path,
                                              "megainfernapeshiny.pal")
            elif output_name == "luxray-mega":
                target_palette = os.path.join(sprite_dir.path, "megaluxray.pal")
            elif output_name == "slaking-mega":
                target_palette = os.path.join(sprite_dir.path,
                                              "megaslaking.pal")
            elif output_name == "dialga-primal":
                target_palette = os.path.join(sprite_dir.path,
                                              "dialgaprimal.pal")
            elif output_name == "palkia-primal":
                target_palette = os.path.join(sprite_dir.path,
                                              "palkiaprimal.pal")
            elif output_name.startswith("alcremie-") and not output_name.endswith("gmax"):
                target_palette = os.path.join(sprite_dir.path, f"{sprite_dir.name}_shiny.pal")

        if not os.path.isfile(target_palette):
            target_palette = os.path.join(sprite_dir.path, "..", "shiny.pal")

        if not os.path.isfile(target_palette):
            continue

        new_sprite = gba_image.swap_palette(
            os.path.join(sprite_dir.path, target_sprite),
            target_palette)

        if new_sprite.width < new_sprite.height:
            if is_icon:
                continue
            new_sprite = new_sprite.crop(
                (0, 0, new_sprite.width, new_sprite.width))

        new_sprite.save(os.path.join(output_dir, "shiny",
                                     f"{output_name}{"-f" if is_female_sprite else ""}.png"))
        _sprite_count += 1
        shiny_sprite_made = True

    if not party_sprite_made:
        print(f"\t\tWARNING: No party sprite found for {output_name}")

    if not sprite_made:
        print(f"\t\tWARNING: No normal palette found for {output_name}")

    if not shiny_sprite_made:
        print(f"\t\tWARNING: No shiny palette found for {output_name}")


def _process_pokemon_sprites(pokemon_dir: str):
    global _sprite_count
    _sprite_count = 0
    print("\tProcessing Pokemon Sprites")
    output = directories.get_output_dir("emerald_imperium/assets/pokemon", True)
    directories.get_output_dir("emerald_imperium/assets/pokemon/party", True)
    directories.get_output_dir("emerald_imperium/assets/pokemon/normal", True)
    directories.get_output_dir("emerald_imperium/assets/pokemon/shiny", True)

    for p_dir in os.scandir(pokemon_dir):
        if not p_dir.is_dir():
            continue

        if p_dir.name != "alcremie":
            _process_pokemon_sprite_images(p_dir, p_dir.name, output)

        for f in os.scandir(p_dir.path):
            if f.is_dir():
                if p_dir.name == "minior" and f.name == "core":
                    for c in os.scandir(f.path):
                        if c.is_dir():
                            _process_pokemon_sprite_images(c,
                                                           f"{p_dir.name}-{f.name}_{c.name}",
                                                           output)
                if p_dir.name == "alcremie":
                    if f.name in [
                        "berry", "clover", "flower", "love", "ribbon", "star",
                        "strawberry"
                    ]:
                        for cream in [
                            "vanilla_cream", "caramel_swirl", "lemon_cream",
                            "matcha_cream", "mint_cream", "rainbow_swirl",
                            "ruby_cream", "ruby_swirl", "salted_cream"
                        ]:
                            _process_pokemon_sprite_images(f,
                                                           f"{p_dir.name}-{f.name}_{cream}",
                                                           output)
                    elif f.name == "gmax":
                        _process_pokemon_sprite_images(f,
                                                       f"{p_dir.name}-{f.name}",
                                                       output)
                else:
                    _process_pokemon_sprite_images(f, f"{p_dir.name}-{f.name}",
                                                   output)

    print(f"\t\t{_sprite_count:n} pokemon sprites generated")


def process():
    print("Processing Sprites")
    root_dir = os.path.join(directories.get_external_dir("emerald-imperium"),
                            "graphics")
    _process_item_sprites(os.path.join(root_dir, "items"))
    _process_pokemon_sprites(os.path.join(root_dir, "pokemon"))
