import logging
import os
import io
import calendar;
import time;

from octoprint.events import Events
from octoprint.util import RepeatedTimer
from octoprint.printer import PrinterCallback

from .config import CrealityConfig
from .crealityprinter import CrealityPrinter, ErrorCode
from .crealitytb import ThingsBoard
from .cxhttp import CrealityAPI

class ProgressMonitor(PrinterCallback):
    def __init__(self, *args, **kwargs):
        super(ProgressMonitor, self).__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        self.printJobTime = None
        self.printLeftTime = None

    def on_printer_send_current_data(self, data):
        self.printJobTime = data["progress"]["printTime"]
        self.printLeftTime = data["progress"]["printTimeLeft"]

class CrealityCloud(object):
    def __init__(self, plugin):
        # cn-shanghai，us-west-1，ap-southeast-1
        self._logger = logging.getLogger("octoprint.plugins.crealitycloud")
        self.plugin = plugin
        self._octoprinter = plugin._printer
        self._config = CrealityConfig(plugin)
        self._video_started = False
        self._aliprinter = None
        self._p2p_service_thread = None
        self._video_service_thread = None
        self._p2p_service_thread = None
        self._video_service_thread = None
        self._active_service_thread = None
        self._iot_connected = False
        self.lk = None
        self.thingsboard = None
        self.timer = False
        self.connect_printer = False
        self.model = ''
        self._printer_disconnect = False
        self._M27_timer_state = False


        self._upload_timer = RepeatedTimer(2,self._upload_timing,run_first=True)
        self._send_M27_timer = RepeatedTimer(10,self._send_M27_timing,run_first=False)
        self._iot_timer = RepeatedTimer(3,self._iot_send_timing,run_first=False)
        self._cxapi = CrealityAPI()
        self.connect_thingsboard()
        
    @property
    def iot_connected(self):
        return self._iot_connected

    def _send_M27_timing(self):
        if self.plugin.printing_befor_connect:
            if self._aliprinter.filename is None:
                self._aliprinter.printer.commands(['M27 C'])
            self._aliprinter.printer.commands(['M27'])
        else:
            self._send_M27_timer.cancel()
            self._M27_timer_state = False

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
            else:
                self._logger.info('tool temperature is none')
            #save bed temperatures data
            if temp_data.get('bed') is not None:
                self._aliprinter.bedTemp = int(temp_data['bed'].get('actual'))
            else:
                self._logger.info('bed temperature is none')

        #get print time
        if self._aliprinter.printer.is_printing():
            if self._progress.printJobTime is not None:
                self._aliprinter.printJobTime = int(self._progress.printJobTime)
                if self._progress.printLeftTime is not None:
                    self._aliprinter.printLeftTime = int(self._progress.printLeftTime)
                else:
                    if self._aliprinter._printTime > 0:
                        self._aliprinter.printLeftTime = int(self._aliprinter._printTime) - int(self._progress.printJobTime)
                    else:
                        try:
                            path = self._aliprinter.plugin._file_manager.path_on_disk(self.print_origin,self.print_path)
                            with io.open(path, mode="r", encoding="utf8", errors="replace") as file:
                                for line in file:
                                    if line[0] != ';':
                                        break
                                    else:
                                        if "TIME" in line:
                                            try:
                                                self._aliprinter._printTime = int(line.replace(";TIME:", ""))
                                            except Exception as e:
                                                self._logger.error(e)
                                        else:
                                            self._aliprinter._printTime = 0
                        except:
                            self._aliprinter.printLeftTime = 0
            else:
                self._aliprinter.printJobTime = 0

    def _iot_send_timing(self):
        self._aliprinter.sendAttributesAndTelemetry()

    def get_server_region(self, regionId):
        if self.config_data.get("region") is not None:
            if self.config_data["region"] == 0:
                return "China"
            else:
                return "US"
        elif regionId is not None:
            if regionId == 0:
                return "China"
            else:
                return "US"
        else:
            return None

    def connect_thingsboard(self):
        self._logger.info("start connect thingsboard")
        self.config_data = self._config.data()
        if self.config_data.get("region") is not None:
            region = self.config_data.get("region")
            if self.config_data.get("iotType") is None or self.config_data.get("iotType") == 1:
                deviceName = self.config_data.get("deviceName")
                productKey = self.config_data.get("productKey")
                deviceSecret = self.config_data.get("deviceSecret")
                result = self._cxapi.exchangeTb(deviceName, productKey, deviceSecret, region)
                if result["result"] is not None:
                    self._config.save("deviceSecret", result["result"]["tbToken"])
                    self._config.save("iotType", 2)
                    thingsboard_Token = result["result"]["tbToken"]
                else:
                    thingsboard_Token = ""
            else:               
                thingsboard_Token = self.config_data["deviceSecret"]

            thingsboard_Id = self.config_data["deviceName"]
            self.thingsboard = ThingsBoard(thingsboard_Id,thingsboard_Token)
            self._iot_connected = self.thingsboard.connect_state
            self.thingsboard.on_server_side_rpc_request = self.on_server_side_rpc_request
            self.thingsboard.client_initialization(region)
            self._aliprinter = CrealityPrinter(self.plugin, self.lk, self.thingsboard)
            self._progress = ProgressMonitor()
            self._aliprinter.printer.register_callback(self._progress)

            self._aliprinter.ipAddress()

            if not self.timer:
                self._upload_timer.start()
                self._send_M27_timer.start()
                self._iot_timer.start()
                self._M27_timer_state = True
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
    
    def on_server_side_rpc_request(self, client, request_id, request_body):
        # self._aliprinter.rpc_client = client
        # self._aliprinter.rpc_requestid = request_id
        if 'method' in request_body.keys():
            method = request_body["method"]
        else:
            return
        if 'params'in request_body.keys():
            params = request_body['params']
        else:
            return
        if method.find('set') >= 0:       
            setReturn = {"code":0}
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
                    setReturn = {"code":-1}
            self.tb_reply_rpc(client, request_id, setReturn)

        elif method.find('get') >= 0:
            getReturn = {"code":0}
            prop_names = list(params.keys())
            for prop_name in prop_names:
                prop_value = params.get(prop_name)
                self._logger.info(
                    "on_thing_prop_changed params:" + prop_name + ":" + str(prop_value)
                )
                try:
                    exec("self._aliprinter." + prop_name + "='" + str(prop_value) + "'")
                    exec("getReturn.update(self._aliprinter." + prop_name + ")")
                except Exception as e:
                    self._logger.error(e)
                    getReturn = {"code":-1}
            self.tb_reply_rpc(client, request_id, getReturn)

    def on_publish_topic(self, mid, userdata):
        self._logger.info("on_publish_topic mid:%d" % mid)

    def on_start(self):
        self._logger.info("plugin started")

    def device_start(self):
        if self.thingsboard is None:
            try:
                self.connect_thingsboard()
            except Exception as e:
                self._logger.error(e)
        if self.thingsboard is not None:
            self._aliprinter.state = 0
            self._aliprinter.printId = ""
            self._aliprinter.tfCard = 1
            self._aliprinter.printer.commands(['M115'])
            if not self._aliprinter.printer.is_closed_or_error():
                self._aliprinter.connect = 1
            else:
                self._aliprinter.connect = 0

    def on_event(self, event, payload):

        if event == Events.CONNECTED:
            if self.thingsboard is not None and not self._M27_timer_state:
                try:
                    self._send_M27_timer.run()
                    self._M27_timer_state = True
                except Exception as e:
                    self._logger.error(e)
            self.device_start()


        if not self._iot_connected:
            return

        if event == Events.STARTUP:

            self._aliprinter.connect = 0
            if os.path.exists("/dev/video0"):
                self._aliprinter.video = 1

        elif event == Events.FIRMWARE_DATA:
            if "MACHINE_TYPE" in payload["data"]:
                self.model = payload["data"]["MACHINE_TYPE"]
                if self.thingsboard is not None:
                    self._aliprinter.model = self.model
            elif "Machine_Name" in payload["data"]:
                self.model = payload["data"]["Machine_Name"]
                if self.thingsboard is not None:
                    self._aliprinter.model = self.model

        elif event == "DisplayLayerProgress_layerChanged":
            self._aliprinter.layer = int(payload["currentLayer"])
            
        elif event == Events.PRINT_FAILED:
            if self._aliprinter.is_cloud_print:
                self._aliprinter.is_cloud_print = False

            if self._aliprinter.stop == 0:
                self._aliprinter.state = 3
                self._aliprinter.error = ErrorCode.PRINT_DISCONNECT.value
                self._aliprinter.printProgress = 0
                self._logger.info("print failed")
        elif event == Events.DISCONNECTED:
            if not self._M27_timer_state:
                try:
                    self._send_M27_timer.cancel()
                    self._M27_timer_state = False
                except Exception as e:
                    self._logger.error(e)
            self._aliprinter.connect = 0

        elif event == Events.PRINT_STARTED:

            if self._aliprinter.is_cloud_print:
                self._aliprinter.mcu_is_print = 0
                self._aliprinter.filename = payload["name"]
            else:
                ts = calendar.timegm(time.gmtime())
                self._aliprinter.printId = "local_" + str(ts)
                self._aliprinter.mcu_is_print = 1

            self._aliprinter.state = 1
            self.print_path = payload["path"]
            self.print_origin = payload["origin"]
            self._progress.reset()
            self._aliprinter._printTime = 0
            self._aliprinter.printLeftTime = 0
            self._aliprinter.printJobTime = 0
            self._aliprinter.printProgress = 0
            
            try:
                path = self._aliprinter.plugin._file_manager.path_on_disk(self.print_origin,self.print_path)
                with io.open(path, mode="r", encoding="utf8", errors="replace") as file:
                    for line in file:
                        if ';----------Shell Config----------------' in line:
                            break
                        elif 'G28 ;Home' in line:
                            break
                        else:
                            if "Print Temperature" in line:
                                nozzleTemp2 = int(line.replace(";Print Temperature:", ""))
                            elif "Bed Temperature" in line:
                                bedTemp2 = int(line.replace(";Bed Temperature:", ""))
                            elif "M140" in line:
                                nozzleTemp2 = int(line.replace("M140 S", ""))
                            elif "M104" in line:
                                bedTemp2 = int(line.replace("M104 S", ""))                                
            except:
                self._logger.info("file not exist")    
            if nozzleTemp2 is not None:
                self._aliprinter.nozzleTemp2 = nozzleTemp2
            
            if bedTemp2 is not None:
                self._aliprinter.bedTemp2 = bedTemp2
                
            #remove gcode in temp folder
            if os.path.exists(self._aliprinter.gcode_file):
                try:
                    os.remove(self._aliprinter.gcode_file)
                except Exception as e:
                    self._logger.error("remove temp file fail! ERROR:" + e)

        elif event == Events.PRINT_PAUSED:
            self._aliprinter.pause = 1

        elif event == Events.PRINT_RESUMED:
            self._aliprinter.pause = 0

        elif event == Events.PRINT_CANCELLED:
            if self._aliprinter.is_cloud_print:
                self._aliprinter.is_cloud_print = False

            self.cancelled = True
            self._aliprinter.error = 1
            self._aliprinter.stop = 2
            self._aliprinter.state = 4
            self._aliprinter.printProgress = 0
            if self._aliprinter.printId.find("local_") >= 0:
                self._aliprinter.mcu_is_print = 0
                self._aliprinter.printId = ""
            

        elif event == Events.PRINT_DONE:
            if self._aliprinter.is_cloud_print:
                self._aliprinter.is_cloud_print = False

            self._aliprinter.state = 2
            if self._aliprinter.printId.find("local_") >= 0:
                self._aliprinter.mcu_is_print = 0
                self._aliprinter.printId = ""
            self._aliprinter.printProgress = 0
            self._aliprinter.printLeftTime = 0
            self._aliprinter.printJobTime = 0

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
            self._aliprinter._tb_send_attributes({"curPosition": self._aliprinter._position})

    def on_progress(self, fileid, progress):
        if progress is not None:
            self._aliprinter.printProgress = progress
            
    def tb_reply_rpc(self, client, request_id, payload):
        if not payload:
            return
        try:
            self._logger.info('tb_reply_rpc:' + str(payload))
            self.thingsboard.reply_rpc(client, request_id, payload)
        except Exception as e:
            self._logger.error(str(e))