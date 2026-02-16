import os.path

import pokelink.directories as directories

_valid_languages = [
    "de",
    "en",
    "es",
    "es-419",
    "fr",
    "it",
    "ja",
    "ko",
    "zh-Hans",
    "zh-Hant"
]

_game_strings = {}


def _load_strings():
    global _game_strings

    if _game_strings.__len__() != 0:
        return

    items_dir = directories.get_external_dir(
        "PKHeX/PKHeX.Core/Resources/text/items/")

    for lang in _valid_languages:
        gs = {}
        lang_file = (lang if lang not in ("zh",
                                          "zh2") else "zh-Hans" if lang == "zh" else "zh-Hant")
        lang_dir = lang if lang not in ("zh",
                                        "zh2") else "zh"

        other = directories.get_external_dir(
            "PKHeX/PKHeX.Core/Resources/text/other/" + lang_dir)

        with open(os.path.join(other, "text_Species_" + lang_file + ".txt"),
                  "r") as species:
            s = []
            for line in species:
                s.append(line.strip())
            gs["species"] = s
            gs["clean_species"] = [clean_up(clean) for clean in s]

        with open(os.path.join(other, "text_Forms_" + lang_file + ".txt"),
                  "r") as forms:
            f = []
            for line in forms:
                if line != "":
                    f.append(line.strip())
            gs["forms"] = f
            gs["clean_forms"] = [clean_up(clean) for clean in f]

        with open(os.path.join(other, "text_Abilities_" + lang_file + ".txt"),
                  "r") as abilities:
            ab = []
            for line in abilities:
                if line != "":
                    ab.append(line.strip())
            gs["abilities"] = ab
            gs["clean_abilities"] = [clean_up(clean) for clean in ab]

        with open(os.path.join(other, "text_Moves_" + lang_file + ".txt"),
                  "r") as abilities:
            ab = []
            for line in abilities:
                if line != "":
                    ab.append(line.strip())
            gs["moves"] = ab
            gs["clean_moves"] = [clean_up(clean) for clean in ab]

        with open(os.path.join(other, "text_Types_" + lang_file + ".txt"),
                  "r") as abilities:
            ab = []
            for line in abilities:
                if line != "":
                    ab.append(line.strip())
            gs["types"] = ab
            gs["clean_types"] = [clean_up(clean) for clean in ab]

        with open(os.path.join(items_dir, "text_Items_" + lang_file + ".txt"),
                  "r") as items:
            i = []
            for line in items:
                if line != "" and not line.startswith("?"):
                    i.append(line.strip())
            gs["items"] = i
            gs["clean_items"] = [clean_up(clean) for clean in i]

        _game_strings[lang] = gs


def has_species(species: str, lang: str = "en") -> bool:
    global _game_strings

    if not _game_strings.__contains__(lang):
        return False

    if not _game_strings[lang].__contains__("species"):
        return False

    return _game_strings[lang]["species"].__contains__(species) or \
        _game_strings[lang]["clean_species"].__contains__(clean_up(species))


def has_form(form: str, lang: str = "en") -> bool:
    global _game_strings

    if not _game_strings.__contains__(lang):
        return False

    if not _game_strings[lang].__contains__("forms"):
        return False

    return _game_strings[lang]["forms"].__contains__(form) or \
        _game_strings[lang]["clean_forms"].__contains__(clean_up(form))


def has_item(item: str, lang: str = "en") -> bool:
    global _game_strings

    if not _game_strings.__contains__(lang):
        return False

    if not _game_strings[lang].__contains__("items"):
        return False

    return _game_strings[lang]["items"].__contains__(item) or \
        _game_strings[lang]["clean_items"].__contains__(clean_up(item))

def has_ability(ability: str, lang: str = "en") -> bool:
    global _game_strings

    if not _game_strings.__contains__(lang):
        return False

    if not _game_strings[lang].__contains__("abilities"):
        return False

    return _game_strings[lang]["abilities"].__contains__(ability) or \
        _game_strings[lang]["clean_abilities"].__contains__(clean_up(ability))

def has_move(move: str, lang: str = "en") -> bool:
    global _game_strings

    if not _game_strings.__contains__(lang):
        return False

    if not _game_strings[lang].__contains__("moves"):
        return False

    return _game_strings[lang]["moves"].__contains__(move) or \
        _game_strings[lang]["clean_moves"].__contains__(clean_up(move))

def has_type(type: str, lang: str = "en") -> bool:
    global _game_strings

    if not _game_strings.__contains__(lang):
        return False

    if not _game_strings[lang].__contains__("types"):
        return False

    return _game_strings[lang]["types"].__contains__(type) or \
        _game_strings[lang]["clean_types"].__contains__(clean_up(type))

def get_type_from_index(index: int, lang: str = "en", return_clean: bool = True) -> str | None:
    types = _game_strings[lang]["clean_types" if return_clean else "types"]

    if types.__len__() <= index:
        return None

    return types[index]


def clean_up(input: str) -> str:
    output = input.lower()

    while output.__contains__("  "):
        output = output.replace("  ", " ")

    output = output.replace("’", "").replace("'", "").replace("é", "e").replace(
        ".", "").replace(" ", "_").replace("-", "_").replace("\u2640",
                                                             "F").replace(
        "\u2642", "M").replace("[", "").replace("]", "").replace(":", "_")

    while output.__contains__("__"):
        output = output.replace("__", "_")

    return output
