from pokelink.core_plugin import _load_plugin
from pokelink.game_strings import _load_strings
import re

def strip_comments(text: str):
    return re.sub("^.*//.*?(\r\n?|\n)", "", text).strip()

print("Loading Pokelink Resources")
_load_strings()
_load_plugin()
print()
