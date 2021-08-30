# coding=utf-8
from __future__ import absolute_import
import time
import uuid
import logging
import threading
import octoprint.plugin
from flask import render_template, request, jsonify
from octoprint.events import Events
from octoprint.server import admin_permission
from .crealitycloud import CrealityCloud
### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import octoprint.plugin

class CrealitycloudPlugin(octoprint.plugin.StartupPlugin,
                       octoprint.plugin.TemplatePlugin,
                       octoprint.plugin.SettingsPlugin,
                       octoprint.plugin.AssetPlugin,
                       octoprint.plugin.EventHandlerPlugin
):
    def __init__(self):
        self._logger = logging.getLogger('octoprint.plugins.crealitycloud')
        self._logger.info("-------------------------------creality cloud init!------------------") 
        #self.crealitycloud = CrealityCloud()
    ##~~ SettingsPlugin mixin

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
            "less": ["less/crealitycloud.less"]
        }
    ##~~ def on_after_startup(self):
    def on_after_startup(self):
        self._logger.info("-------------------------------creality cloud stared!------------------") 

    def on_event(self, event, payload):
        if event == Events.FIRMWARE_DATA:
            if "MACHINE_TYPE" in payload["data"]:
                machine_type = payload["data"]["MACHINE_TYPE"]
                self._settings.set(['machine_type'], machine_type)
                self._settings.save()


        if event == Events.PRINT_STARTED:
            self.crealitycloud.on_event(state=0)

        if event == Events.PRINT_CANCELLED:
            self.cancelled = True

        if event == Events.PRINT_DONE:
            # 完成消息
            self.crealitycloud.on_event(state=1)

        if event == Events.CONNECTED:
            # reboot消息
            # self._logger.info("notify remote reboot ...")
            self.crealitycloud.on_event(state=2)

        if event == Events.PRINTER_STATE_CHANGED:
            if payload["state_id"] == "OPERATIONAL":
                # cancelled 的任务状态变为operational时，发送完成消息
                if self.cancelled:
                    self.cloud_task.on_event(state=0, continue_code="stop")
                    self.cancelled = False
                #printer_manager = printer_manager_instance(self)
                #printer_manager.clean_file()

    ##~~ Softwareupdate hook

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


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Crealitycloud Plugin"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
#__plugin_pythoncompat__ = ">=2.7,<3" # only python 2
#__plugin_pythoncompat__ = ">=3,<4" # only python 3
#__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3
__plugin_pythoncompat__ = ">=2.7,<4"
def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = CrealitycloudPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
