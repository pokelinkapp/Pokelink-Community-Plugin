import os
import zipfile
from sys import platform

_core_plugin_files = []


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

    zip_f = zipfile.ZipFile(plugin_path)

    _core_plugin_files = ['/' + name for name in zip_f.namelist()]

    zip_f.close()


def file_exists(file: str) -> bool:
    global _core_plugin_files
    return _core_plugin_files.__contains__(file)
