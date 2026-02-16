import os
import zipfile
from sys import platform
from zipfile import ZipFile

_core_plugin_files = []
_zip_f: ZipFile

def _load_plugin():
    global _core_plugin_files
    if _core_plugin_files.__len__() != 0:
        return
    if platform == "win32":
        plugin_path = os.path.abspath(
            os.path.join(os.environ["APPDATA"], "..", "Local", "Pokelink"))
    else:
        plugin_path = os.path.abspath(
            os.path.join(os.environ["HOME"], ".local", "share", "pokelink"))

    plugin_path = os.path.abspath(
        os.path.join(plugin_path, "resources", "public.zcell"))

    global _zip_f
    _zip_f = zipfile.ZipFile(plugin_path)

    _core_plugin_files = ["/" + name for name in _zip_f.namelist()]


def file_exists(file: str) -> bool:
    global _core_plugin_files
    return _core_plugin_files.__contains__(file)

def read_file(file: str) -> bytes | None:
    if not file_exists(file):
        return None
    return _zip_f.read(file.removeprefix("/"))