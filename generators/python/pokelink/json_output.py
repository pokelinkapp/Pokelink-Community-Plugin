import json


def write_file(path: str, data: object):
    with open(path, "w") as write:
        json.dump(data, write, indent="  ")