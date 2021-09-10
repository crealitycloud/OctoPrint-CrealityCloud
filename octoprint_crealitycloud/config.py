import json
import logging
import os


class CreailtyConfig(object):
    def __init__(self, plugin) -> None:
        self._path = self.path = os.path.join(
            plugin.get_plugin_data_folder(), "config.json"
        )
        self._p2p_path = self.path = os.path.join(
            plugin.get_plugin_data_folder(), "p2pcfg.json"
        )
        self._logger = logging.getLogger("octoprint.plugins.config")
        self._logger.debug(self._path)
        self._p2pdata = {}
        self._data = {}
        if os.path.exists(self._path):
            with open(self._path, "r") as f:
                self._data = json.load(f)
                f.close()
        if os.path.exists(self._p2p_path):
            with open(self._p2p_path, "r") as f:
                self._p2pdata = json.load(f)
                f.close()

    def data(self):
        return self._data

    def p2p_data(self):
        return self._p2pdata

    def save(self, key, val):
        self._data[key] = val
        with open(self._path, "w") as f:
            json.dump(self._data, f)
            f.close()

    def save_p2p_config(self, key, val):
        self._p2pdata[key] = val
        with open(self._p2p_path, "w") as f:
            json.dump(self._p2pdata, f)
            f.close()
