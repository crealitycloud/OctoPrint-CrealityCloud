# coding=utf-8
from __future__ import absolute_import

import logging
import os
import threading
import time
import uuid

import octoprint.plugin
from flask import jsonify, render_template, request
from linkkit.linkkit import LinkKit
from octoprint.events import Events
from octoprint.server import admin_permission

from .crealitycloud import CrealityCloud
from .cxhttp import CrealityAPI

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.


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
            "-------------------------------creality cloud init!------------------"
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
        self._logger.info(
            "-------------------------------creality cloud stared!------------------"
        )
        self._crealitycloud.on_start()

    def on_event(self, event, payload):
        self._crealitycloud.on_event(event, payload)

    ##~~ Softwareupdate hook
    def on_print_progress(self, storage, path, progress):
        print(storage)
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
                "user": "hemiao218",
                "repo": "OctoPrint-Crealitycloud",
                "current": self._plugin_version,
                # update method: pip
                "pip": "https://github.com/hemiao218/OctoPrint-Crealitycloud/archive/{target_version}.zip",
            }
        }

    def get_template_configs(self):
        return [dict(type="settings", custom_bindings=True)]

    def get_assets(self):
        return dict(
            js=["js/crealitycloud.js", "js/qrcode.min.js"], css=["css/crealitycloud.css"]
        )

    @octoprint.plugin.BlueprintPlugin.route("/makeQR", methods=["GET", "POST"])
    def make_qr(self):
        if os.path.exists(self.get_plugin_data_folder() + "/code"):
            os.remove(self.get_plugin_data_folder() + "/code")
        country = request.json["country"]
        self._crealitycloud.start_active_service(country)
        return {"code": 0}

    @octoprint.plugin.BlueprintPlugin.route("/machineqr", methods=["GET"])
    def get_machine_short_id(self):
        code_path = self.get_plugin_data_folder() + "/code"
        if os.path.exists(code_path):
            with open(code_path, "r") as f:
                self.short_code = f.readline()
                f.close()
                return {"code": self.short_code}
        else:
            return {"code": "0"}

    @octoprint.plugin.BlueprintPlugin.route("/status", methods=["GET"])
    def get_status(self):
        country = self._addr[1]
        if os.path.exists(self.get_plugin_data_folder() + "/config.json"):
            if not self._crealitycloud.iot_connected:
                self._logger.info("start iot server")
                os.system("/usr/bin/sync")
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
        print(cmd)
        if cmd[0] != "M":
            return cmd
        else:
            if "M220 S" in cmd:
                self._crealitycloud._aliprinter._curFeedratePct = cmd.lstrip("M220 S")
                self._crealitycloud._aliprinter._upload_data(
                    {
                        "curFeedratePct": int(
                            self._crealitycloud._aliprinter._curFeedratePct
                        )
                    }
                )
                print(self._crealitycloud._aliprinter._curFeedratePct)
            if "M27" in cmd:
                if "c" in cmd:
                    return
                    # filename = cmd.
                else:
                    return

    def gCodeHandlerreceived(self, comm_instance, line, *args, **kwargs):
        if "SD printing byte " in line:
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
            self._crealitycloud._aliprinter._percent = float(
                (float(leftnum) / float(rightnum) )* 100
            )
            return line
        if "Current file: " in line:
            self._crealitycloud._aliprinter._filename = str(str(line).lstrip("Current file: ")).rsplit("\n")
            return line
        return line


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Crealitycloud Plugin"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
# __plugin_pythoncompat__ = ">=2.7,<3" # only python 2
# __plugin_pythoncompat__ = ">=3,<4" # only python 3
# __plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = CrealitycloudPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.gCodeHandlerSent,
        "octoprint.comm.protocol.gcode.received": __plugin_implementation__.gCodeHandlerreceived,
    }
