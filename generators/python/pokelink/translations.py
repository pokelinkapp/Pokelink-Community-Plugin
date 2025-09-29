import json
import os

_translations = {"code": "", "translations": {}}


def add_translation(key: str, value: str):
    split = key.split(".")
    last = split[-1]
    split.remove(last)
    current = _translations["translations"]

    for i in split:
        if not current.__contains__(i):
            current[i] = {}
        current = current[i]

    current[last] = value

    return


def clear():
    global _translations
    _translations = {"code": "", "translations": {}}


def write_translations(output_path: str, code: str = "en-GB"):
    _translations["code"] = code

    if not os.path.isdir(output_path + "/" + code + "/"):
        os.makedirs(output_path + "/" + code + "/")

    with open(output_path + "/" + code + "/generated.lang", "w") as write:
        json.dump(_translations, write, indent="  ", ensure_ascii=False)

    return
