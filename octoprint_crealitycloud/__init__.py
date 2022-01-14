# coding=utf-8
from __future__ import absolute_import

import logging
import os
import json
import io

import octoprint.plugin
from flask import request

from .crealitycloud import CrealityCloud
from .cxhttp import CrealityAPI


class CrealitycloudPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.ProgressPlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.BlueprintPlugin,
):
    def __init__(self):
        self._logger = logging.getLogger("octoprint.plugins.crealitycloud")
        self._logger.info(
            "creality cloud init!"
        )
        self.short_code = None
        self._addr = None

    def initialize(self):
        self._crealitycloud = CrealityCloud(self)
        self._cxapi = CrealityAPI()
        try:
            self._addr = self._cxapi.getAddrress1()
        except:
            try:
                self._addr = self._cxapi.getAddrress2()
            except:
                self._addr = ("", "US")

    def get_settings_defaults(self):
        return {
            # put your plugin's default settings here
        }

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/crealitycloud.js"],
            "css": ["css/crealitycloud.css"],
            "less": ["less/crealitycloud.less"],
        }

    ##~~ def on_after_startup(self):
    def on_after_startup(self):
        self._logger.info("creality cloud stared!")
        self._crealitycloud.on_start()

    def on_event(self, event, payload):
        self._crealitycloud.on_event(event, payload)

    ##~~ Softwareupdate hook
    def on_print_progress(self, storage, path, progress):
        self._crealitycloud.on_progress(storage, progress)

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "crealitycloud": {
                "displayName": "Crealitycloud Plugin",
                "displayVersion": self._plugin_version,
                # version check: github repository
                "type": "github_release",
                "user": "crealitycloud",
                "repo": "OctoPrint-Crealitycloud",
                "current": self._plugin_version,
                # update method: pip
                "pip": "https://github.com/crealitycloud/OctoPrint-Crealitycloud/archive/{target_version}.zip",
            }
        }

    def get_template_configs(self):
        return [dict(type="settings", custom_bindings=True)]

    def get_assets(self):
        return dict(
            js=["js/crealitycloud.js", "js/qrcode.min.js"], css=["css/crealitycloud.css"]
        )

    #get token
    @octoprint.plugin.BlueprintPlugin.route("/get_token", methods=["POST"])
    def get_token(self):
        try:
            self._res = self._cxapi.getconfig(request.json["token"])["result"]
            if self._res["regionId"] == 0:
                region = 0
            else:
                region = 1
            self._config = {
                "deviceName": self._res["deviceName"],
                "deviceSecret": self._res["deviceSecret"],
                "productKey": self._res["productKey"],
                "region": region
                }
            with io.open(
                self.get_plugin_data_folder()+'/config.json', "w", encoding="utf-8"
            ) as config_file:
                json.dump(self._config,config_file, indent=2, separators=(',',':'))
                self._logger.info(self._config)
            return {"code": 0}
        except Exception as e:
            self._logger.error(str(e))
            return {"code": -1}

    @octoprint.plugin.BlueprintPlugin.route("/status", methods=["GET"])
    def get_status(self):
        country = self._addr[1]
        if os.path.exists(self.get_plugin_data_folder() + "/config.json"):
            if not self._crealitycloud.iot_connected:
                self._logger.info("start iot server")
                self._crealitycloud.device_start()
                if self._crealitycloud.get_server_region() is not None:
                    country = self._crealitycloud.get_server_region()
            return {
                "actived": 1,
                "iot": self._crealitycloud.iot_connected,
                "printer": self._printer.is_operational(),
                "country": country,
            }
        else:
            return {"actived": 0, "iot": False, "printer": False, "country": country}

    # get gcode return
    def gCodeHandlerSent(
        self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs
    ):
        if gcode == "M220":
            self._crealitycloud._aliprinter._str_curFeedratePct = cmd

    def gCodeHandlerreceived(self, comm_instance, line, *args, **kwargs):
        leftnum = 0
        rightnum = 0
        if not self._crealitycloud._iot_connected:
            return line
        if "SD printing byte " in line:
            self._crealitycloud._aliprinter.mcu_is_print = 1
            self._crealitycloud._aliprinter.state = 1
            leftnum = ""
            rightnum = ""
            percentstr = line.lstrip("SD printing byte ")
            for i in percentstr:
                if i == "/":
                    rightnum = str(percentstr.lstrip(leftnum)).rstrip("\r\n")
                    rightnum = rightnum.lstrip("/")
                    break
                leftnum = leftnum + str(i)
            self._crealitycloud._aliprinter.printProgress = int(
                (float(leftnum) / float(rightnum)) * 100
            )
            return line
        elif "Current file: " in line:
            self._crealitycloud._aliprinter.filename = line
            return line
        elif "Not SD printing" in line:
            if (
                    self._crealitycloud._aliprinter.mcu_is_print == 1
                and not self._crealitycloud._aliprinter.printer.is_printing()
            ):
                
                if (
                    not self._crealitycloud._aliprinter.printId
                    and ((float(leftnum) / float(rightnum)) * 100) > 99.9
                ):
                    self._crealitycloud._aliprinter.state = 2
                    self._crealitycloud._aliprinter.printProgress = 0
                else:
                    self._crealitycloud._aliprinter.state = 0
                    self._crealitycloud._aliprinter.printProgress = 0
                self._crealitycloud._aliprinter.mcu_is_print == 0
                
        return line


__plugin_name__ = "Crealitycloud Plugin"

__plugin_pythoncompat__ = ">=3,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = CrealitycloudPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.gCodeHandlerSent,
        "octoprint.comm.protocol.gcode.received": __plugin_implementation__.gCodeHandlerreceived,
    }
