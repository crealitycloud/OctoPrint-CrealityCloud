import json
import logging
import os


class CreailtyConfig(object):
    def __init__(self, plugin) -> None:
        self._path = self.path = os.path.join(
            plugin.get_plugin_data_folder(), "config.json"
        )
        self._logger = logging.getLogger("octoprint.plugins.config")
        print(self._path)
        with open(self._path, "r") as f:
            self._data = json.load(f)

    def data(self):
        return self._data

    def save(self):
        with open("data.json", "w") as f:
            json.dump(self._data, f)
