from PIL import Image


def swap_palette(image_path: str, palette_path: str) -> Image.Image:
    new_palette = []

    with open(palette_path) as palette_file:
        for line in [clean.strip() for clean in palette_file]:
            sections = line.split(" ")

            if sections.__len__() < 3:
                continue

            new_palette += [
                int(sections[0]), int(sections[1]), int(sections[2]),
                0 if new_palette.__len__() == 0 else 255
            ]

    with Image.open(image_path) as sprite:
        new_sprite = Image.new("P", sprite.size)
        new_sprite.putpalette(new_palette, rawmode="RGBA")
        new_sprite.paste(sprite, (0, 0) + sprite.size)

        return new_sprite


def remove_icon_background(image_path: str, background_index=0) -> Image.Image:
    with Image.open(image_path) as sprite:
        new_sprite = Image.new("P", sprite.size)
        new_palette = sprite.getpalette("RGBA")
        new_palette[(background_index * 4) + 3] = 0
        new_sprite.putpalette(new_palette, rawmode="RGBA")
        new_sprite.paste(sprite, (0, 0) + sprite.size)

        return new_sprite
