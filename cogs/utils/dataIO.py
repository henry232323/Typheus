# A utility for writing json without longhand LBYL checks for reading / writing
# Original here: https://github.com/Twentysix26/Red-DiscordBot/blob/develop/cogs/utils/dataIO.py

import ujson as json
import os
import logging
from random import randint

class InvalidFileIO(Exception):
    pass

class DataIO():
    def __init__(self):
        self.logger = logging.getLogger("red")

    def save_json(self, filename, data):
        mypath = r'{}'.format(filename)
        """Atomically saves json file"""
        rnd = randint(1000, 9999)
        path, ext = os.path.splitext(filename)
        tmp_file = "{}-{}.tmp".format(path, rnd)
        self._save_json(tmp_file, data)
        try:
            self._read_json(tmp_file)
        except json.decoder.JSONDecodeError:
            self.logger.exception(filename + " integrity check failed")
            return False
        os.replace(tmp_file, filename)
        return True

    def load_json(self, filename):
        """Loads json file"""
        return self._read_json(filename)

    def is_valid_json(self, filename):
        """Verifies if json file exists / is readable"""
        try:
            self._read_json(filename)
            return True
        except FileNotFoundError:
            return False
        except json.decoder.JSONDecodeError:
            return False

    def _read_json(self, filename):
        with open(filename, encoding='utf-8', mode="r") as f:
            data = json.load(f)
        return data

    def _save_json(self, filename, data):
        dir =filename.split('/')
        del dir[-1]
        dir = '/'.join(dir)
        if not os.path.exists(dir):
            directory = filename.split('/')
            del directory[-1]
            os.makedirs('/'.join(directory)) 
        with open(filename, encoding='utf-8', mode="w") as f:
            json.dump(data, f, indent=4,sort_keys=True,
                separators=(',',' : '))
        return data


def get_value(filename, key):
    with open(filename, encoding='utf-8', mode="r") as f:
        data = json.load(f)
    return data[key]

def set_value(filename, key, value):
    data = fileIO(filename, "load")
    data[key] = value
    fileIO(filename, "save", data)
    return True

dataIO = DataIO()
