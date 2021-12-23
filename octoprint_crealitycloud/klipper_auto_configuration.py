# coding=utf-8
from __future__ import absolute_import

import io
import json
import logging
import os
import os.path


class auto_klipper:
    def __init__(self):
        self._logger = logging.getLogger("octoprint.plugins.crealitycloud")
        self._id = 0
        self._firmware_path = ""
        self._config_path = ""
        self._pricfg_path = ""
        self._printer_path = ""
        self._firmware = ""
        self._id = 0

        # get user path
        self._user_path = os.path.expanduser("~")

    def set_id(self,id):
        self._id = id
        
    def set_path(self):
        with io.open(
            os.path.dirname(os.path.abspath(__file__)) + "/config/model.json",
            "r",
            encoding="utf8",
        ) as _modellist_data:
            _modellist = json.load(_modellist_data)
            templist = _modellist["modellist"][int(self._id)]
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
                self._user_path + "/printer.cfg", "r", encoding="utf-8"
            ) as r_printer:  # 创建一个读对象
                for i in r_printer:  # 逐行读取printer.cfg内容
                    print(i)
                    if "serial: /dev/" in i:
                        i = "serial: " + serial_port_name + "\n"
                    data += i

            with io.open(
                self._user_path + "/printer.cfg", "w", encoding="utf-8"
            ) as w_printer:  # 创建一个写对象
                w_printer.write(data.decode("utf8"))

            return True
        else:
            return False

    def get_fwname(self):
        return self._firmware
    
    def get_json(self):
        with io.open(
            os.path.dirname(os.path.abspath(__file__)) + "/config/model.json",
            "r",
            encoding="utf8",
        ) as file_data:
            file_json = json.load(file_data)
            return file_json

    def set_status_json(self,status):
        with io.open(
            os.path.dirname(os.path.abspath(__file__)) + "/config/model.json",
            "r",
            encoding="utf8",
        ) as read_json:
            data = json.load(read_json)
            data["model"] = self._id
            data['klipperable'] = status
        with io.open(
            os.path.dirname(os.path.abspath(__file__)) + "/config/model.json",
            "w",
            encoding="utf8",
        ) as write_json:
            json.dump(data,write_json)
