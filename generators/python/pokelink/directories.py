import os

external = "../../external/"
output = "../../pokelink-community/"


def get_external_dir(folder: str) -> str:
    path = os.path.abspath(os.path.join(external, folder))
    if os.path.isdir(path):
        return os.path.abspath(path)
    raise NotADirectoryError(os.path.abspath(path))


def get_output_dir(folder: str, create: bool = False) -> str:
    path = os.path.abspath(os.path.join(output, folder))
    if os.path.isdir(path):
        return path

    if create:
        os.makedirs(path)
        return path
    raise NotADirectoryError(os.path.abspath(path))
