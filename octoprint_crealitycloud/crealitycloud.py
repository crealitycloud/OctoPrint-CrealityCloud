import logging
import os
import subprocess
import threading
import time
from asyncio.windows_events import NULL

from linkkit import linkkit
from octoprint.events import Events

from .config import CreailtyConfig
from .crealityprinter import CrealityPrinter, ErrorCode
from .perpetual_timer import PerpetualTimer


class CrealityCloud(object):
    def __init__(self, plugin):
        # cn-shanghai，us-west-1，ap-southeast-1
        self._logger = logging.getLogger("octoprint.plugins.crealitycloud")
        self.plugin = plugin
        self._octoprinter = plugin._printer
        self._config = CreailtyConfig(plugin)
        self._video_started = False
        # self.config_data = self._config.data()
        self._aliprinter = None
        self._report_timer = PerpetualTimer(5, self.report_temperatures)
        self._report_sdprinting_timer = PerpetualTimer(5, self.report_printerstatus)
        self._check_printer_status = PerpetualTimer(5,self.check_printer_status)
        self._report_boxversion = PerpetualTimer(5,self.report_boxversion)
        self._report_curFeedratePct = PerpetualTimer(5,self.report_curFeedratePct)
        self._p2p_service_thread = None
        self._video_service_thread = None

        self._p2p_service_thread = None
        self._video_service_thread = None
        self._active_service_thread = None
        self._iot_connected = False
        self.lk = None
        self.connect_aliyun()

    @property
    def iot_connected(self):
        return self._iot_connected

    def get_server_region(self):
        if self.config_data.get("region") is not None:
            if self.config_data["region"] == 0:
                return "China"
            else:
                return "US"
        else:
            return None

    def connect_aliyun(self):
        self._logger.info("start connect aliyun")
        self.config_data = self._config.data()
        if self.config_data.get("region") is not None:
            self.lk = linkkit.LinkKit(
                host_name=self.region_to_string(self.config_data["region"]),
                product_key=self.config_data["productKey"],
                device_name=self.config_data["deviceName"],
                device_secret=self.config_data["deviceSecret"],
            )
            self._iot_connected = True
            self.lk.enable_logger(logging.WARNING)
            self.lk.on_device_dynamic_register = self.on_device_dynamic_register
            self.lk.on_connect = self.on_connect
            self.lk.on_disconnect = self.on_disconnect
            self.lk.on_topic_message = self.on_topic_message
            self.lk.on_subscribe_topic = self.on_subscribe_topic
            self.lk.on_unsubscribe_topic = self.on_unsubscribe_topic
            self.lk.on_publish_topic = self.on_publish_topic
            self.lk.on_thing_prop_changed = self.on_thing_prop_changed
            self.lk.on_thing_prop_post = self.on_thing_prop_post
            self.lk.on_thing_raw_data_arrived = self.on_thing_raw_data_arrived
            self.lk.on_thing_raw_data_arrived = self.on_thing_raw_data_arrived
            self.lk.thing_setup()
            self.lk.connect_async()
            self._logger.info("aliyun loop")
            self._aliprinter = CrealityPrinter(self.plugin, self.lk)

    def region_to_string(self, num):
        regions = {
            0: "cn-shanghai",
            1: "ap-southeast-1",
            2: "ap-northeast-1",
            3: "us-west-1",
            4: "eu-central-1",
            5: "us-east-1",
        }
        return regions.get(num)

    def on_thing_shadow_get(self, payload, userdata):
        self._logger.info("prop data:%r" % self.rawDataToProtocol(payload))

    def on_thing_raw_data_arrived(self, payload, userdata):
        self._logger.info("on_thing_raw_data_arrived:%r" % payload)
        self._logger.info("prop data:%r" % self.rawDataToProtocol(payload))

    def on_thing_raw_data_post(self, payload, userdata):
        self._logger.info("on_thing_raw_data_post: %s" % str(payload))

    def rawDataToProtocol(self, byte_data):
        alink_data = {}
        head = byte_data[0]
        if head == 0x01:
            alink_data["method"] = "thing.service.property.set"
            alink_data["version"] = "1.0"
            alink_data["id"] = int.from_bytes(byte_data[1:5], "big")
            params = {}
            params["prop_int16"] = int.from_bytes(byte_data[5:7], "big")
            alink_data["params"] = params
            return alink_data

    def on_thing_prop_post(self, request_id, code, data, message, userdata):
        self._logger.info(
            "on_thing_prop_post request id:%s, code:%d, data:%s message:%s"
            % (request_id, code, str(data), message)
        )

    def on_device_dynamic_register(self, rc, value, userdata):
        if rc == 0:
            self._logger.info("dynamic register device success, value:" + value)
        else:
            self._logger.info("dynamic register device fail, message:" + value)

    def on_connect(self, session_flag, rc, userdata):
        self._logger.info("on_connect:%d,rc:%d" % (session_flag, rc))
        pass

    def on_disconnect(self, rc, userdata):
        self._logger.info("on_disconnect:rc:%d,userdata:" % rc)

    def on_topic_message(self, topic, payload, qos, userdata):
        self._logger.info(
            "on_topic_message:" + topic + " payload:" + str(payload) + " qos:" + str(qos)
        )
        pass

    def on_subscribe_topic(self, mid, granted_qos, userdata):
        self._logger.info(
            "on_subscribe_topic mid:%d, granted_qos:%s"
            % (mid, str(",".join("%s" % it for it in granted_qos)))
        )
        pass

    def on_unsubscribe_topic(self, mid, userdata):
        self._logger.info("on_unsubscribe_topic mid:%d" % mid)
        pass

    def on_thing_prop_changed(self, params, userdata):
        prop_names = list(params.keys())
        for prop_name in prop_names:
            prop_value = params.get(prop_name)
            self._logger.info("on_thing_prop_changed params:" + prop_name + ":" + str(prop_value))
            exec("self._aliprinter." + prop_name + "='" + str(prop_value) + "'")

    def on_publish_topic(self, mid, userdata):
        self._logger.info("on_publish_topic mid:%d" % mid)

    def on_start(self):
        self._logger.info("plugin started")

    def video_start(self):
        initString = self._config.p2p_data().get("InitString")
        didString = self._config.p2p_data().get("DIDString")
        apiLicense = self._config.p2p_data().get("APILicense")
        prop_data = {
            "InitString": initString if initString is not None else "",
            "DIDString": didString if didString is not None else "",
            "APILicense": apiLicense if apiLicense is not None else "",
        }

        self.lk.thing_post_property(prop_data)
        if initString is None:
            return
        self.start_video_service()
        time.sleep(2)  # wait video process started
        self.start_p2p_service()
        self._logger.info("video service started")

    def device_start(self):
        if self.lk is not None:
            if os.path.exists("/dev/video0"):
                self._aliprinter.video = 1
                self.video_start()
            else:
                self._aliprinter.video = 0
            self._aliprinter.state = 0
            self._aliprinter.printId = ""
            self._aliprinter.connect = 1
            self._aliprinter.tfCard = 1
            self._report_timer.start()
            self._report_sdprinting_timer.start()
            self._check_printer_status.start()
            self._report_curFeedratePct.start()
        else:
            self.connect_aliyun()

    def on_event(self, event, payload):

        if event == Events.CONNECTED:
            self.device_start()

        if not self._iot_connected:
            return

        if event == "Startup":
            self._report_boxversion.start()
            self._aliprinter.connect = 0
            if os.path.exists("/dev/video0"):
                self._aliprinter.video = 1

        if event == Events.FIRMWARE_DATA:
            if "MACHINE_TYPE" in payload["data"]:
                machine_type = payload["data"]["MACHINE_TYPE"]
                if self.lk is not None:
                    self._aliprinter.model = machine_type

        if event == "DisplayLayerProgress_layerChanged":
            self._aliprinter.layer = int(payload["currentLayer"])
        if event == "CrealityCloud-Video":
            self.video_start()
        if event == Events.PRINT_FAILED:
            if self._aliprinter.stop == 0:
                self._aliprinter.state = 3
                self._aliprinter.error = ErrorCode.PRINT_DISCONNECT.value
                self._aliprinter.printId = ""
                self._logger.info("print failed")
        if event == Events.DISCONNECTED:
            self._aliprinter.connect = 0
            self._report_timer.cancel()
            self._report_sdprinting_timer.cancel()
            self._check_printer_status.cancel()
            self._report_curFeedratePct.cancel()

        if event == Events.PRINT_STARTED:
            self._aliprinter.state = 1

        if event == Events.PRINT_PAUSED:
            self._aliprinter.pause = 1

        if event == Events.PRINT_RESUMED:
            self._aliprinter.pause = 0

        if event == Events.PRINT_CANCELLED:
            self.cancelled = True

        if event == Events.PRINT_DONE:
            self._aliprinter.state = 0

        # get M114 payload
        if event == Events.POSITION_UPDATE:
            self._aliprinter._xcoordinate = payload["x"]
            self._aliprinter._ycoordinate = payload["y"]
            self._aliprinter._zcoordinate = payload["z"]
            self._aliprinter._position = (
                "X:"
                + str(payload["x"])
                + " Y:"
                + str(payload["y"])
                + " Z:"
                + str(payload["z"])
            )

        # get local ip address
        if event == Events.CONNECTIVITY_CHANGED:
            if payload["new"] == True:
                self._aliprinter.ipAddress

    def on_progress(self, fileid, progress):
        self._aliprinter.printProgress = progress

    def check_printer_status(self):
        if self._aliprinter.printer.is_printing() == False:
            self._aliprinter.state = 0
        else:
            self._aliprinter.state = 1

    def report_printerstatus(self):
        self._aliprinter.printer.commands(["M27"])
        self._aliprinter.printer.commands(["M27C"])
        if self._aliprinter._filename and self._aliprinter._percent and self._aliprinter._mcu_is_print != 0:
            filename = str(self._aliprinter._filename[0])
            filename = filename.replace('GCO','gcode')
            print (filename)
            self._aliprinter._upload_data({"print":filename})
            self._aliprinter._upload_data({"printProgress":int(self._aliprinter._percent)})
            self._aliprinter._upload_data({"mcu_is_print":self._aliprinter._mcu_is_print})
        elif self._aliprinter._mcu_is_print == 0:
            self._aliprinter._upload_data({"mcu_is_print":self._aliprinter._mcu_is_print})
            self._aliprinter._filename = ""
            self._aliprinter._mcu_is_print = ""
        return

    def report_temperatures(self):
        if self._iot_connected is False:
            return
        data = self._octoprinter.get_current_temperatures()
        if not data:
            self._logger.error("can't get temperatures")
        else:
            if data.get("tool0") is not None:
                self._aliprinter.nozzleTemp = data["tool0"].get("actual")
                self._aliprinter.nozzleTemp2 = data["tool0"].get("target")
            if data.get("bed") is not None:
                self._aliprinter.bedTemp = data["bed"].get("actual")
                self._aliprinter.bedTemp2 = data["bed"].get("target")

	#Report box version until success
    def report_boxversion(self):
        if self._aliprinter.bool_boxVersion != True:
            try:
                self._aliprinter.boxVersion = self._aliprinter._boxVersion
            except:
                pass
            else:
                self.bool_boxVersion = True
                self._report_boxversion.cancel()
        else:
            self._report_boxversion.cancel()

    def report_curFeedratePct(self):
        if self._aliprinter._curFeedratePct == "":
            return
        else:
            try:
                self._aliprinter.curFeedratePct = self._aliprinter._curFeedratePct.lstrip("M220 S")
            except Exception as e:
                self._logger.error(e)

    def start_active_service(self, country):
        if self._active_service_thread is not None:
            self._active_service_thread = None
        env = os.environ.copy()
        env["HOME_LOG"] = self.plugin.get_plugin_data_folder()
        env["OCTO_DATA_DIR"] = self.plugin.get_plugin_data_folder()
        env["REGION"] = country
        importcode_path = (
            os.path.dirname(os.path.abspath(__file__)) + "/bin/importcode.sh"
        )
        dest_importcode_path = self.plugin.get_plugin_data_folder() + "/importcode.sh"
        if os.path.exists(dest_importcode_path):
            os.remove(dest_importcode_path)
        os.system("cp " + importcode_path + " " + dest_importcode_path)
        active_service_path = (
            os.path.dirname(os.path.abspath(__file__)) + "/bin/active_server.sh"
        )
        self._active_service_thread = threading.Thread(
            target=self._runcmd, args=(["/bin/bash", active_service_path], env)
        )
        self._active_service_thread.start()

    def start_p2p_service(self):
        if self._p2p_service_thread is not None:
            self._p2p_service_thread = None
        p2p_service_path = (
            os.path.dirname(os.path.abspath(__file__)) + "/bin/p2p_server.sh"
        )
        if not os.path.exists(p2p_service_path):
            return
        if self._config.p2p_data().get("APILicense") is not None:
            env = os.environ.copy()

            env["HOME_LOG"] = self.plugin.get_plugin_data_folder()
            env["APILicense"] = self._config.p2p_data().get("APILicense")
            env["DIDString"] = self._config.p2p_data().get("DIDString")
            env["InitString"] = self._config.p2p_data().get("InitString")
            env["RtspPort"] = "8554"
            self._p2p_service_thread = threading.Thread(
                target=self._runcmd, args=(["/bin/bash", p2p_service_path], env)
            )
            self._p2p_service_thread.start()

    def start_video_service(self):
        if self._video_service_thread is not None:
            self._video_service_thread = None
        video_service_path = (
            os.path.dirname(os.path.abspath(__file__)) + "/bin/rtsp_server.sh"
        )
        if self._config.p2p_data().get("APILicense") is not None:
            env = os.environ.copy()
            self._video_service_thread = threading.Thread(
                target=self._runcmd, args=(["/bin/bash", video_service_path], env)
            )
            self._video_service_thread.start()

    def _runcmd(self, command, env):
        popen = s