import json
import logging
import os


class CrealityConfig(object):
    def __init__(self, plugin) -> None:
        self._path = self.path = os.path.join(
            plugin.get_plugin_data_folder(), "config.json"
        )
        self._p2p_path = self.path = os.path.join(
            plugin.get_plugin_data_folder(), "p2pcfg.json"
        )
        self._p2pdata = {}
        self._data = {}
        self.load()

    def load(self):
        if os.path.exists(self._path):
            with open(self._path, "r") as f:
                try:
                    self._data = json.load(f)
                except:
                    os.remove(self._path)
        if os.path.exists(self._p2p_path):
            with open(self._p2p_path, "r") as f:
                try:
                    self._p2pdata = json.load(f)
                except:
                    os.remove(self._p2p_path)

    def data(self):
        self.load()
        return self._data

    def p2p_data(self):
        self.load()
        return self._p2pdata

    def save(self, key, val):
        self._data[key] = val
        with open(self._path, "w") as f:
            json.dump(self._data, f)

    def save_p2p_config(self, key, val):
        self._p2pdata[key] = val
        with open(self._p2p_path, "w") as f:
            json.dump(self._p2pdata, f)
