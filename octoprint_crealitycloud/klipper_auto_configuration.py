# coding=utf-8
from __future__ import absolute_import

import io
import json
import logging
import os
import os.path


class auto_klipper:
    def __init__(self, id):
        self._logger = logging.getLogger("octoprint.plugins.crealitycloud")
        self._id = 0
        self._firmware_path = ""
        self._config_path = ""
        self._pricfg_path = ""
        self._printer_path = ""
        self._firmware = ""

        # set model name
        self._id = id

        # get user path
        self._user_path = os.path.expanduser("~")

    def set_path(self):
        with io.open(
            os.path.dirname(os.path.abspath(__file__)) + "/model.json",
            "r",
            encoding="utf8",
        ) as _modellist_data:
            _modellist = json.load(_modellist_data)
            templist = _modellist["modellist"][int(self._id)]
            model = templist["model"]
            pricfg = templist["pricfg"]
            cfg = templist["cfg"]
            self._firmware = templist["firmware"]

            # set firmware path
            self._firmware_path = os.path.dirname(os.path.abspath(__file__)) + "/firmware/" + self._firmware
            self._logger.info("cp " + self._firmware_path + " " + self._user_path + "/.octoprint/uploads/" + self._firmware)
            os.popen("cp " + self._firmware_path + " " + self._user_path + "/.octoprint/uploads/" + self._firmware)

            # set .concfg path
            self._config_path = os.path.dirname(os.path.abspath(__file__)) + "/config/" + cfg
            self._logger.info("cp " + self._config_path + " " + self._user_path + "/klipper/.config")
            os.popen("cp " + self._config_path + " " + self._user_path + "/klipper/.config" )

            # set printer.cfg path
            self._pricfg_path = self._user_path + "/klipper/config/" + pricfg
            self._logger.info("............................." + "cp " + self._pricfg_path + " " + self._user_path + "/printer.cfg" +".....................")
            os.popen("cp " + self._pricfg_path + " " + self._user_path + "/printer.cfg")

    def change_serial(self):
        # get seerial
        try:
            val = os.popen("ls /dev/serial/by-id/*")
        except Exception:
            return False

        if val != None and os.path.isfile(self._printer_path):

            for temp in val:
                serial_port_name = str(temp)

            data = ""
            with io.open(
                "/home/pi/printer.cfg", "r", encoding="utf-8"
            ) as r_printer:  # 创建一个读对象
                for i in r_printer:  # 逐行读取printer.cfg内容
                    print(i)
                    if "serial: /dev/" in i:
                        i = "serial: " + serial_port_name + "\n"
                    data += i

            with io.open(
                "/home/pi/printer.cfg", "w", encoding="utf-8"
            ) as w_printer:  # 创建一个写对象
                w_printer.write(data.decode("utf8"))

            return True
        else:
            return False

    def get_fwname(self):
        return self._firmware
