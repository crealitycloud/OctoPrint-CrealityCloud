import gzip
import logging
import os
import socket
import tempfile
import threading
import time
import uuid
from contextlib import closing
from enum import Enum

import octoprint
import octoprint.filemanager.analysis
import octoprint.filemanager.storage
import octoprint.plugin
import octoprint.slicing
import octoprint.util
import psutil
import requests
from octoprint.events import Events, eventManager
from octoprint.filemanager.destinations import FileDestinations

from octoprint_crealitycloud.filecontrol import filecontrol

from .config import CreailtyConfig


class ErrorCode(Enum):
    UNKNOW = 0
    STOP = 1
    DOWNLOAD_FAIL = 2
    PRINT_DISCONNECT = 3
    BREAK_SERIAL = 4
    NO_PRINTABLE = 5
    HEAT_FAIL = 6
    SYSTEM_HALT = 7
    SYSTEM_TIMOUT = 8
    NO_TFCARD = 9
    NO_SPLACE = 10


class CrealityPrinter(object):
    def __init__(self, plugin, lk):

        self._logger = logging.getLogger("octoprint.plugins.crealityprinter")
        self._config = CreailtyConfig(plugin)
        self._filecontrol = filecontrol(plugin)
        self.__linkkit = lk
        self.settings = plugin._settings
        self.printer = plugin._printer
        self.plugin = plugin
        self.Filemanager = self._filecontrol.Filemanager
        self._boxVersion = "rasp_v2.01b99"
        self._state = -1
        self._stop = 0
        self._pause = 0
        self._connected = 0
        self._printProgress = -1
        self._mcu_is_print = -1
        self._printId = ''
        self._nozzleTemp = -1
        self._nozzleTemp2 = -1
        self._bedTemp = -1
        self._bedTemp2 = -1
        self._position = ''
        self._curFeedratePct = 0
        self._dProgress = 0
        self._reqGcodeFile = None
        self._opGcodeFile = None
        self._filename = None
        self._gcodeCmd = None
        self._APILicense = None
        self._initString = None
        self._DIDString = None
        self.bool_boxVersion = None
        self._str_curFeedratePct = ""
        self._logger.info("creality crealityprinter init!")

    def __setitem__(self, k, v):
        self._logger.info("__setitem__:" + k)
        self.__dict__[k] = v

    def _upload_data(self, payload):
        if not payload:
            return
        try:
            self.__linkkit.thing_post_property(payload)
        except Exception as e:
            self._logger.error(str(e))

    @property
    def printId(self):
        return self._printId

    @printId.setter
    def printId(self, v):
        self._printId = v
        self._upload_data({"printId": self._printId})

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self,v):
        if 'no file' not in v:
            if v != self._filename:
                self._filename = v  
                filename = str(str(v).lstrip("Current file: ")).rsplit("\n")
                filename = str(filename[0])
                filename = filename.replace("GCO", "gcode")
                self._upload_data({"print": str(filename)})

    @property
    def print(self):
        return self._print

    @print.setter
    def print(self, url):
        self._print = url
        self.layer = 0
        printId = str(uuid.uuid1()).replace("-", "")
        self.state = 0
        self.dProgress = 0
        self._download_thread = threading.Thread(
            target=self._process_file_request, args=(url, printId)
        )
        self._download_thread.start()

    @property
    def video(self):
        return self._video

    @video.setter
    def video(self, v):
        self._video = v
        self._upload_data({"video": v})

    @property
    def ReqPrinterPara(self):
        return self._ReqPrinterPara

    # get Position and Feedrate data
    @ReqPrinterPara.setter
    def ReqPrinterPara(self, v):
        self._ReqPrinterPara = int(v)
        if self._ReqPrinterPara == 0:
            self._upload_data({"curFeedratePct": self._curFeedratePct})
        # if self._ReqPrinterPara == 1:
            if self.printer.is_operational() and not self.printer.is_printing():
                self._autohome = 1
                self.printer.commands(["M114"])
                self._upload_data({"curPosition": self._position,
                                    "autohome": 1})
            else:
                self._autohome = 0

    # get files infomation and upload
    @property
    def reqGcodeFile(self):
        return self._reqGcodeFile

    # upload filelist
    @reqGcodeFile.setter
    def reqGcodeFile(self, v):
        page = int(v) & 0x0000FFFF
        origin = int(v) >> 16
        file_list = self._filecontrol.repfile(origin, page)
        self._upload_data({"retGcodeFileInfo": file_list})

    # upload curFeedratePct
    @property
    def curFeedratePct(self):
        return self._curFeedratePct

    @curFeedratePct.setter
    def curFeedratePct(self, v):
        if self._curFeedratePct != v:
            self._curFeedratePct = int(v)
            self.printer.feed_rate(self._curFeedratePct)
            self._upload_data({"curFeedratePct": self._curFeedratePct})

    # get local ip address show in the CrealityCloud App
    @property
    def ipAddress(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
            self._upload_data({"netIP": ip})
            return ip

    # sent gCode
    @property
    def gcodeCmd(self):
        return self._gcodeCmd

    @gcodeCmd.setter
    def gcodeCmd(self, v):
        self._gcodeCmd = v
        if v is not None:
            self.printer.commands([v])

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, v):
        if int(v) != int(self._state):
            self._state = v
            self._upload_data({"state": self._state})

    @property
    def dProgress(self):
        return self._dProgress

    @dProgress.setter
    def dProgress(self, v):
        self._dProgress = v
        self._upload_data({"dProgress": self._dProgress})

    @property
    def connect(self):
        return self._connected

    @property
    def error(self):
        return self._error

    @error.setter
    def error(self, v):
        self._error = v
        self._upload_data({"err": self._error})
        self._logger.info("post error:" + str(self._error))

    @connect.setter
    def connect(self, v):
        self._connected = v
        self._upload_data({"connect": self._connected})

    @property
    def pause(self):
        return self._pause

    @pause.setter
    def pause(self, v):
        self._pause = int(v)
        self._upload_data({"pause": self._pause})
        if self._pause == 0:
            if self.printer.is_paused():
                self.printer.resume_print()
                self.state = 1
        if self._pause == 1:
            if not self.printer.is_paused():
                self.printer.pause_print()
                self.state = 5

    @property
    def tfCard(self):
        return self._tfCard

    @tfCard.setter
    def tfCard(self, v):
        self._tfCard = v
        self._upload_data({"tfCard": self._tfCard})

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, v):
        self._model = v
        self._upload_data({"model": self._model})

    @property
    def stop(self):
        return self._stop

    @stop.setter
    def stop(self, v):
        self._stop = int(v)
        if self._stop == 1:
            self.state = 4
            self.printer.cancel_print()

    @property
    def nozzleTemp(self):
        return self._nozzleTemp

    @nozzleTemp.setter
    def nozzleTemp(self, v):
        if int(v) != int(self.nozzleTemp):
            self._nozzleTemp = int(v)
            self._upload_data({"nozzleTemp": int(self._nozzleTemp)})

    @property
    def nozzleTemp2(self):
        return self._nozzleTemp2

    @nozzleTemp2.setter
    def nozzleTemp2(self, v):
        if int(v) != int(self._nozzleTemp2):
            self._nozzleTemp2 = int(v)
            self._upload_data({"nozzleTemp2": int(self._nozzleTemp2)})
            self.printer.set_temperature("tool0", int(v))

    @property
    def bedTemp(self):
        return self._bedTemp

    @bedTemp.setter
    def bedTemp(self, v):
        if int(v) != int(self._bedTemp):
            self._bedTemp = int(v)
            self._upload_data({"bedTemp": int(self._bedTemp)})

    @property
    def bedTemp2(self):
        return self._bedTemp2

    @bedTemp2.setter
    def bedTemp2(self, v):
        if int(v) != int(self._bedTemp2):
            self._bedTemp2 = int(v)
            self._upload_data({"bedTemp2": self._bedTemp2})
            self.printer.set_temperature("bed", int(v))

    @property
    def mcu_is_print(self):
        return self._mcu_is_print

    @mcu_is_print.setter
    def mcu_is_print(self, v):
        if int(v) != self._mcu_is_print:
            self._mcu_is_print = int(v)
            self._upload_data({"mcu_is_print": self._mcu_is_print})

    @property
    def boxVersion(self):
        return self._boxVersion

    @boxVersion.setter
    def boxVersion(self, v):
        self._upload_data({"boxVersion": self._boxVersion})

    @property
    def printProgress(self):
        return ""

    @printProgress.setter
    def printProgress(self, v):
        if int(v) != self._printProgress:
            self._printProgress = v
            self._upload_data({"printProgress": self._printProgress})

    @property
    def layer(self):
        return self._layer

    @layer.setter
    def layer(self, v):
        self._layer = v
        self._upload_data({"layer": self._layer})

    @property
    def InitString(self):
        return self._initString

    @InitString.setter
    def InitString(self, v):
        self._initString = v
        self._config.save_p2p_config("InitString", v)
        self._upload_data({"InitString": self._initString})

    @property
    def APILicense(self):
        return self._APILicense

    @APILicense.setter
    def APILicense(self, v):
        self._APILicense = v
        self._config.save_p2p_config("APILicense", v)
        self._upload_data({"APILicense": self._APILicense})

    @property
    def DIDString(self):
        return self._DIDString

    @DIDString.setter
    def DIDString(self, v):
        self._DIDString = v
        self._config.save_p2p_config("DIDString", v)
        self._upload_data({"DIDString": self._DIDString})
        eventManager().fire("CrealityCloud-Video", {})

    @property
    def fan(self):
        return self._fan

    @fan.setter
    def fan(self, v):
        self._fan = int(v)
        if self._fan == 1:
            self.printer.commands(["M106"])
        else:
            self.printer.commands(["M107"])
        self._upload_data({"fan": self._fan})

    @property
    def autohome(self):
        return self._autohome

    @autohome.setter
    def autohome(self, v):
        if v == 0:
            axes = []
            self._autohome = v
            if "x" in self._autohome:
                axes.append("x")
            if "y" in self._autohome:
                axes.append("y")
            if "z" in self._autohome:
                axes.append("z")
            self.printer.home(axes)

    @property
    def printStartTime(self):
        return self._printStartTime

    @printStartTime.setter
    def printStartTime(self, v):
        self._printStartTime = v
        self._upload_data({"printStartTime": str(self._printStartTime)})

    def _process_file_request(self, download_url, new_filename):
        from octoprint.filemanager.destinations import FileDestinations
        from octoprint.filemanager.util import DiskFileWrapper

        # Free space usage
        free = psutil.disk_usage(
            self.settings.global_get_basefolder("uploads", check_writable=False)
        ).free

        self._logger.info(
            "Downloading new file, name: {}, free space: {}".format(new_filename, free)
        )
        new_filename = os.path.basename(download_url)
        # response.content currently contains the file's content in memory, now write it to a temporary file
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(
            temp_dir, "crealitycloud-file-upload-{}".format(new_filename)
        )

        gcode_file = os.path.join(temp_dir, os.path.splitext(new_filename)[0])

        if os.path.exists(gcode_file) == False:
            self.download(download_url, temp_path)
            gfile = gzip.GzipFile(temp_path)
            open(gcode_file, "wb+").write(gfile.read())
            gfile.close()
            os.remove(temp_path)
        self._logger.info("Copying file to filemanager:" + gcode_file)
        upload = DiskFileWrapper(os.path.splitext(new_filename)[0], gcode_file)

        try:
            canon_path, canon_filename = self.plugin._file_manager.canonicalize(
                FileDestinations.LOCAL, upload.filename
            )
            future_path = self.plugin._file_manager.sanitize_path(
                FileDestinations.LOCAL, canon_path
            )
            future_filename = self.plugin._file_manager.sanitize_name(
                FileDestinations.LOCAL, canon_filename
            )
        except Exception as e:
            # Most likely the file path is not valid for some reason
            self._logger.exception(e)
            return False

        future_full_path = self.plugin._file_manager.join_path(
            FileDestinations.LOCAL, future_path, future_filename
        )
        future_full_path_in_storage = self.plugin._file_manager.path_in_storage(
            FileDestinations.LOCAL, future_full_path
        )

        # Check the file is not in use by the printer (ie. currently printing)
        if not self.printer.can_modify_file(
            future_full_path_in_storage, False
        ):  # args: path, is sd?
            self._logger.error("Tried to overwrite file in use")
            return False

        try:
            added_file = self.plugin._file_manager.add_file(
                FileDestinations.LOCAL,
                future_full_path_in_storage,
                upload,
                allow_overwrite=True,
                display=canon_filename,
            )
        except octoprint.filemanager.storage.StorageError as e:
            self._logger.error(
                "Could not upload the file {}".format(future_full_path_in_storage)
            )
            self._logger.exception(e)
            return False

        # Select the file for printing
        self.printer.select_file(
            future_full_path_in_storage,
            False,  # SD?
            True,  # Print after select?
        )

        # Fire file uploaded event
        payload = {
            "name": future_filename,
            "path": added_file,
            "target": FileDestinations.LOCAL,
            "select": True,
            "print": True,
            "app": True,
        }
        eventManager().fire(Events.UPLOAD, payload)
        self._logger.debug("Finished uploading the file")

        # Remove temporary file (we didn't forget about you!)
        try:
            os.remove(temp_path)
        # except FileNotFoundError:
        #    pass
        except Exception:
            self._logger.warning("Failed to remove file at {}".format(temp_path))
        self.state = 1
        self.printStartTime = int(time.time())
        # We got to the end \o/
        # Likely means everything went OK
        return True

    def download(self, url, file_path):  # bug
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36"
        }
        with closing(requests.get(url, headers=headers, stream=True)) as response:
            chunk_size = 1024  # 单次请求最大值
            content_size = int(response.headers["content-length"])  # 内容体总大小
            data_count = 0
            now_time = time.time()
            with open(file_path, "wb") as file:
                for data in response.iter_content(chunk_size=chunk_size):
                    file.write(data)
                    data_count = data_count + len(data)
                    now_jd = (data_count / content_size) * 100

                    if time.time() - now_time > 2:
                        now_time = time.time()
                        self.dProgress = int(now_jd)
        self.dProgress = 100

    @property
    def opGcodeFile(self):
        return self._opGcodeFile

    # file control
    @opGcodeFile.setter
    def opGcodeFile(self, v):
        if "print" in v:
            if "local" in v:
                target = FileDestinations.LOCAL
                filename = str(v).lstrip("printbox:/local/")
                filenameToSelect = self.Filemanager.path_on_disk(target, filename)
                sd = False
                printAfterLoading = True
                self.printer.select_file(
                    filenameToSelect,
                    sd,
                    printAfterLoading,
                )
        else:
            self._filecontrol.controlfiles(v)
