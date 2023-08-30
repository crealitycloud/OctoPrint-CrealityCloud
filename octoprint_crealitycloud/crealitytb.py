import logging
from tb_device_mqtt import TBDeviceMqttClient, TBPublishInfo
import time
import psutil
import json

class ThingsBoard(object):
    def __init__(self, devicename, credentials):
        self._logger = logging.getLogger("octoprint.plugins.crealitycloud")
        self._provision_device_key = "73li9vss6hr3vr8c6fev"
        self._provision_device_secret = "32ph6nlshnd2e6kil9we"
        self._host = "mqtt.crealitycloud.cn"
        self.devicename = devicename
        self.credentials = credentials
        self.id = None
        self.client = None
        self.client_attributes_keys = ""
        self.shared_attributes_keys = ""
        self.telemetry = {"nozzleTemp": 0, "bedTemp": 0, "curFeedratePct": 0,"dProgress": 0, "printProgress": 0,"printJobTime": 0, "printLeftTime": 0}
        self.attributes = {"printStartTime": " ","layer": 0,"printedTimes": 0,"timesLeftToPrint": 0 
                        ,"err": 0,"curPosition":" ","printId":" ","filename":" ","video": 0,"netIP":" ","state": 0,"tfCard": 0,"model":" "
                        ,"mcu_is_print": 0,"boxVersion":" ","InitString":" ","APILicense":" ","DIDString":" ","retGcodeFileInfo":" ","autohome": 0
                        ,"fan": 0,"stop": 0,"print":" ","nozzleTemp2": 0,"bedTemp2": 0,"pause": 0,"opGcodeFile":" ","gcodeCmd":" ","setPosition":" ","tag":"1.0.8", "led_state": 0}
        self.__on_server_side_rpc_request = None

    def client_initialization(self, region):
        if region != 0:
            self._host = "mqtt.crealitycloud.com"
        self.__client_create()
        self.__respond_rpc()
        self.__client_connect()
        self.__init_shadow()

    def client_provison(self):
        self.credentials = TBDeviceMqttClient.provision(self._host, self._provision_device_key, self._provision_device_secret, device_name=self.id)
        
    def request_attributes(self):
        self.client.request_attributes(self.client_attributes_keys, self.shared_attributes_keys, callback = self.__on_attributes_change)
        while not self.client.stopped:
            time.sleep(1)
            
    def send_telemetry(self, payload):
        self.client.send_telemetry(payload)
    
    def send_attributes(self, payload):
        self.client.send_attributes(payload)
    
    def reply_rpc(self, client, request_id, payload):
        client.send_rpc_reply(request_id, json.dumps(payload))
    
    def connect_state(self):
        return self.client.is_connected

    def __client_create(self):
        self.client = TBDeviceMqttClient(self._host, self.credentials)

    def __client_connect(self):
        try:
            self.client.connect(timeout=90, keepalive=30)
        except Exception as e:
            self._logger.error(str(e))
        
    def __respond_rpc(self):
        if self.__on_server_side_rpc_request is not None:
            self.client.set_server_side_rpc_request_handler(self.__on_server_side_rpc_request)
    
    def __init_shadow(self):
        self.send_telemetry(self.telemetry)
        self.send_attributes(self.attributes)

    def __on_attributes_change(self, client, result, exception):
        if exception is not None:
            return True
        else:
            return False

    @property
    def on_server_side_rpc_request(self):
        return self.__on_server_side_rpc_request

    @on_server_side_rpc_request.setter
    def on_server_side_rpc_request(self, value):
        self.__on_server_side_rpc_request = value
        pass
