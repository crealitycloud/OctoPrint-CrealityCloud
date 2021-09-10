import logging
import os
import subprocess
import threading

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
        self.config_data = self._config.data()
        self.connect_aliyun(
            self.config_data["region"],
            self.config_data["productKey"],
            self.config_data["deviceName"],
            self.config_data["deviceSecret"],
        )
        self._aliprinter = CrealityPrinter(plugin, self.lk)
        self._report_timer = PerpetualTimer(5, self.report_temperatures)

        self._p2p_service_thread = None
        self._video_service_thread = None

    def connect_aliyun(self, region, pk, dn, ds):
        self.lk = linkkit.LinkKit(
            host_name=self.region_to_string(region),
            product_key=pk,
            device_name=dn,
            device_secret=ds,
        )
        # current_dir = os.path.dirname(os.path.abspath(__file__))

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
        # self.lk.on_thing_shadow_get = self.on_thing_shadow_get
        self.lk.thing_setup()
        self.lk.connect_async()
        self.lk.start_worker_loop()

    def region_to_string(self, num):
        regions = {0: "cn-shanghai", 1: "us-west-1", 2: "ap-southeast-1"}
        return regions.get(num)

    def on_thing_shadow_get(self, payload, userdata):
        print("prop data:%r" % self.rawDataToProtocol(payload))

    def on_thing_raw_data_arrived(self, payload, userdata):
        print("on_thing_raw_data_arrived:%r" % payload)
        print("prop data:%r" % self.rawDataToProtocol(payload))

    def on_thing_raw_data_post(self, payload, userdata):
        print("on_thing_raw_data_post: %s" % str(payload))

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
        print(
            "on_thing_prop_post request id:%s, code:%d, data:%s message:%s"
            % (request_id, code, str(data), message)
        )

    def on_device_dynamic_register(self, rc, value, userdata):
        if rc == 0:
            print("dynamic register device success, value:" + value)
        else:
            print("dynamic register device fail, message:" + value)

    def on_connect(self, session_flag, rc, userdata):
        print("on_connect:%d,rc:%d" % (session_flag, rc))
        pass

    def on_disconnect(self, rc, userdata):
        print("on_disconnect:rc:%d,userdata:" % rc)

    def on_topic_message(self, topic, payload, qos, userdata):
        print(
            "on_topic_message:" + topic + " payload:" + str(payload) + " qos:" + str(qos)
        )
        pass

    def on_subscribe_topic(self, mid, granted_qos, userdata):
        print(
            "on_subscribe_topic mid:%d, granted_qos:%s"
            % (mid, str(",".join("%s" % it for it in granted_qos)))
        )
        pass

    def on_unsubscribe_topic(self, mid, userdata):
        print("on_unsubscribe_topic mid:%d" % mid)
        pass

    def on_thing_prop_changed(self, params, userdata):
        prop_names = list(params.keys())
        for prop_name in prop_names:
            prop_value = params.get(prop_name)
            print("on_thing_prop_changed params:" + prop_name + ":" + str(prop_value))
            exec("self._aliprinter." + prop_name + "='" + str(prop_value) + "'")

    def on_publish_topic(self, mid, userdata):
        print("on_publish_topic mid:%d" % mid)

    def on_start(self):
        prop_data = {
            "InitString": self._config.p2p_data().get("InitString"),
            "APILicense": self._config.p2p_data().get("APILicense"),
            "DIDString": self._config.p2p_data().get("DIDString"),
        }
        self.lk.thing_post_property(prop_data)
        if os.path.exists("/dev/video0"):
            self.start_video_service()
            self.start_p2p_service()
            self._aliprinter.video = 1
        else:
            self._aliprinter.video = 0

    def on_event(self, event, payload):
        if event == Events.FIRMWARE_DATA:
            if "MACHINE_TYPE" in payload["data"]:
                machine_type = payload["data"]["MACHINE_TYPE"]
                self._aliprinter.model = machine_type
                self._aliprinter.boxVersion = "octo_v1.01b1"
        if event == Events.CONNECTED:
            self._aliprinter.state = 0
            self._aliprinter.printId = ""
            self._aliprinter.connect = 1
            self._report_timer.start()

        if event == "DisplayLayerProgress_layerChanged":
            self._aliprinter.layer = payload["currentLayer"]

        if event == Events.PRINT_FAILED:
            self._aliprinter.state = 3
            self._aliprinter.error = ErrorCode.PRINT_DISCONNECT.value
            self._aliprinter.printId = ""
            print("print failed")
        if event == Events.DISCONNECTED:
            self._aliprinter.connect = 0
            self._report_timer.cancel()

        if event == Events.PRINT_STARTED:
            self._aliprinter.state = 1

        if event == Events.PRINT_PAUSED:
            self._aliprinter.pause = 1

        if event == Events.PRINT_RESUMED:
            self._aliprinter.pause = 0

        if event == Events.PRINT_CANCELLED:
            self.cancelled = True

        if event == Events.PRINT_DONE:
            # 完成消息
            self._aliprinter.state = 0
        # if event == Events.UPLOAD:
        #    if payload["app"] is True:
        #        self._octoprinter.start_print()

        if event == Events.CONNECTED:
            self._aliprinter.connect = 1

        if event == Events.DISCONNECTED:
            self._aliprinter.connect = 0
            self._report_timer.cancel()

        if event == Events.PRINTER_STATE_CHANGED:
            if payload["state_id"] == "OPERATIONAL":
                # cancelled 的任务状态变为operational时，发送完成消息
                if self._aliprinter.stop:
                    self._aliprinter.state = 0
            # if payload["state_id"] == "OFFLINE":
            #    if self._aliprinter.state == 1:
            #        self._aliprinter.state = 3
            #        self._aliprinter.error = ErrorCode.PRINT_DISCONNECT

            # printer_manager = printer_manager_instance(self)
            # printer_manager.clean_file()

    def on_progress(self, fileid, progress):
        self._aliprinter.printProgress = progress

    def report_temperatures(self):
        self.lk.thing_get_shadow()
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
            self._logger.info(
                str(self._aliprinter.nozzleTemp)
                + "----"
                + str(self._aliprinter.bedTemp)
                + "---"
                + str(self._octoprinter.is_printing())
            )
        # self._report_timer.start()
        # self._aliprinter.nozzleTemp2 =2

    def start_p2p_service(self):
        if self._p2p_service_thread is not None:
            self._p2p_service_thread.cancel()
        p2p_service_path = (
            os.path.dirname(os.path.abspath(__file__)) + "/bin/p2p_server.sh"
        )
        if not os.path.exists(p2p_service_path):
            return
        if self._config.p2p_data().get("APILicense") is not None:
            env = os.environ.copy()
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
            self._video_service_thread.cancel()
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
        popen = subprocess.Popen(command, env=env)
        return_code = popen.wait()
        if return_code == 0:
            self._logger.info("_runcmd success:", return_code)
        else:
            self._logger.error("_runcmd error:", return_code)
