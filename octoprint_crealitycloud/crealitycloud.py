import logging
import os
import shutil
import subprocess
import threading
import time
import sys
from gettext import find

from linkkit import linkkit
from octoprint.events import Events
from octoprint.util import RepeatedTimer

from .config import CreailtyConfig
from .crealityprinter import CrealityPrinter, ErrorCode


class CrealityCloud(object):
    def __init__(self, plugin, recorderObject):
        # cn-shanghai，us-west-1，ap-southeast-1
        self._logger = logging.getLogger("octoprint.plugins.crealitycloud")
        self.plugin = plugin
        self._octoprinter = plugin._printer
        self._config = CreailtyConfig(plugin)
        self._video_started = False
        self._aliprinter = None
        self._p2p_service_thread = None
        self._video_service_thread = None
        self._p2p_service_thread = None
        self._video_service_thread = None
        self._active_service_thread = None
        self._iot_connected = False
        self.lk = None
        self.timer = False
        self.connect_printer = False
        self.model = ''
        self._printer_disconnect = False

        self._upload_timer = RepeatedTimer(2,self._upload_timing,run_first=True)
        self._upload_ip_timer = RepeatedTimer(30,self._upload_ip_timing,run_first=False)
        self._send_M27_timer = RepeatedTimer(10,self._send_M27_timing,run_first=False)

        self.connect_aliyun()
        self.recorder = recorderObject
        self.pipe = "/tmp/rpfifo"
        self.pipein = None
        self.init_pipe()
        self._read_pipe_timer = RepeatedTimer(0.5, self.read_pipe_play, run_first=True)
        self._read_pipe_timer.start()
    @property
    def iot_connected(self):
        return self._iot_connected

    def _send_M27_timing(self):
        self._aliprinter.printer.commands(['M27'])
        self._aliprinter.printer.commands(['M27C'])

    def _upload_ip_timing(self):
        self._aliprinter.ipAddress
        self._upload_ip_timer.cancel()

    def _upload_timing(self):
            
        if self._aliprinter.printer.is_closed_or_error():
            if not self._printer_disconnect:
                self._logger.info('disconnect printer or printer error')
                self._printer_disconnect = True
            return

        self._printer_disconnect = False
        #upload box verson
        if self._aliprinter.bool_boxVersion != True:
            self._aliprinter.boxVersion = self._aliprinter._boxVersion
            self._aliprinter.bool_boxVersion = True

        #report curFeedratePct
        if self._aliprinter._str_curFeedratePct:
            try:
                S_location = self._aliprinter._str_curFeedratePct.find("S")
                int_curfeedratepct = self._aliprinter._str_curFeedratePct[
                    S_location + 1 : len(self._aliprinter._str_curFeedratePct)
                ]
                self._aliprinter.curFeedratePct = int(int_curfeedratepct)
            except Exception as e:
                self._logger.error(e)

        #get temperatures data
        temp_data = self._octoprinter.get_current_temperatures()
        if not temp_data:
            self._logger.info("can't get temperatures")
        else:
            #save tool0 temperatures data
            if temp_data.get('tool0') is not None:
                self._aliprinter.nozzleTemp = int(temp_data['tool0'].get('actual'))
                self._aliprinter.nozzleTemp2 = int(temp_data['tool0'].get('target'))
            else:
                self._logger.info('tool temperature is none')
            #save bed temperatures data
            if temp_data.get('bed') is not None:
                self._aliprinter.bedTemp = int(temp_data['bed'].get('actual'))
                self._aliprinter.bedTemp2 = int(temp_data['bed'].get('target'))
            else:
                self._logger.info('bed temperature is none')

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
            time.sleep(3)
            self._upload_ip_timer.start()
            if not self.timer:
                self._upload_timer.start()
                self._send_M27_timer.start()
                self.timer = True


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
            self._logger.info(
                "on_thing_prop_changed params:" + prop_name + ":" + str(prop_value)
            )
            try:
                exec("self._aliprinter." + prop_name + "='" + str(prop_value) + "'")
            except Exception as e:
                self._logger.error(e)

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
        if self.lk is None:
            try:
                self.connect_aliyun()
            except Exception as e:
                self._logger.error(e)

        self._aliprinter.state = 0
        self._aliprinter.printId = ""
        self._aliprinter.connect = 1
        self._aliprinter.tfCard = 1
        self._aliprinter.printer.commands(['M115'])
        if not self._aliprinter.printer.is_closed_or_error():
            self._aliprinter.connect = 1
        if os.path.exists("/dev/video0"):
            self._aliprinter.video = 1
            self.video_start()
        else:
            self._aliprinter.video = 0

    def on_event(self, event, payload):

        if event == Events.CONNECTED:
            self.device_start()


        if not self._iot_connected:
            return

        if event == "Startup":

            self._aliprinter.connect = 0
            if os.path.exists("/dev/video0"):
                self._aliprinter.video = 1

        elif event == Events.FIRMWARE_DATA:
            if "MACHINE_TYPE" in payload["data"]:
                self.model = payload["data"]["MACHINE_TYPE"]
                if self.lk is not None:
                    self._aliprinter.model = self.model

        elif event == "DisplayLayerProgress_layerChanged":
            self._aliprinter.layer = int(payload["currentLayer"])
        elif event == "CrealityCloud-Video":
            self.video_start()
        elif event == Events.PRINT_FAILED:
            if self._aliprinter.stop == 0:
                self._aliprinter.state = 3
                self._aliprinter.error = ErrorCode.PRINT_DISCONNECT.value
                self._aliprinter._printId = ""
                self._logger.info("print failed")
        elif event == Events.DISCONNECTED:
            self._aliprinter.connect = 0
            self.recorder.stop()

        elif event == Events.PRINT_STARTED:
            if not self._aliprinter.printId:
                self._aliprinter.mcu_is_print = 1
            self._aliprinter.state = 1
            if self._aliprinter.printId != "" and os.path.exists("/dev/video0"):
                self.recorder.set_printid(self._aliprinter.printId)
                self.recorder.run()
                self._logger.info('printid:' + str(self._aliprinter.printId))
                
        elif event == Events.PRINT_PAUSED:
            self._aliprinter.pause = 1

        elif event == Events.PRINT_RESUMED:
            self._aliprinter.pause = 0

        elif event == Events.PRINT_CANCELLED:
            self.cancelled = True
            self._aliprinter._upload_data({"err": 1, "stop": 1, "state": 4, "printId": self._aliprinter._printId})
            if not self._aliprinter.printId:
                self._aliprinter.mcu_is_print = 0
            self._aliprinter._printId = ""
            self.recorder.stop()

        elif event == Events.PRINT_DONE:
            self._aliprinter.state = 2
            self.recorder.stop()
            if not self._aliprinter.printId:
                self._aliprinter.mcu_is_print = 0
            self._aliprinter._printId = ""
			
        # get M114 payload
        elif event == Events.POSITION_UPDATE:
            self._aliprinter._position = (
                "X:"
                + str(payload["x"])
                + " Y:"
                + str(payload["y"])
                + " Z:"
                + str(payload["z"])
            )
            self._aliprinter._upload_data({"curPosition": self._aliprinter._position})

    def on_progress(self, fileid, progress):
        self._aliprinter.printProgress = progress

    def check_printer_status(self):
        if self._aliprinter.printer.is_printing() == True:
            self._aliprinter.state = 1

    # Report box version until success
    def report_boxversion(self):
        if self._iot_connected is False or self._aliprinter.connect == 0:
            return
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

    def gcode_curFeedratePct(self):
        if not self._aliprinter._str_curFeedratePct:
            return
        else:
            try:
                S_location = self._aliprinter._str_curFeedratePct.find("S")
                int_curfeedratepct = self._aliprinter._str_curFeedratePct[
                    S_location + 1 : len(self._aliprinter._str_curFeedratePct)
                ]
                self._aliprinter.curFeedratePct = int(int_curfeedratepct)
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
            return
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
            return
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

    def init_pipe(self):
        if not os.path.exists(self.pipe):
            os.mkfifo(self.pipe, 0o777)         
        self.pipein = os.open(self.pipe, os.O_RDONLY | os.O_NONBLOCK)

    def read_pipe_play(self):
        line = os.read(self.pipein,128)
        line = line.decode()
        head = line.find('OPTIONS')
        stop = line.find('session closed remote')
        if stop == -1 and head >= 0 :   
            live = line.find('ch0_0')
            replay = line.find('rec-tick-')
            if live > 0:
                l = threading.Thread(target=self.recorder.play, args=('ch0_0',))
                l.start()     
            elif replay > 0:
                line = line[replay : ]
                tail = line.find('.h264')
                line = line[ : tail + 5]
                #line = line.replace('.h264', '', 1).replace('rec-tick-', '', 1)              
                if line != 'rec-tick-0.h264':
                    r = threading.Thread(target=self.recorder.play, args=(line,))
                    r.start()       
        # elif stop != -1:
        #     self.recorder.stop_play()
        
