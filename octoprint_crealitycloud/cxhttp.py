import json
import random
import uuid
import requests


class CrealityAPI(object):
    def __init__(self):
        self.__homeurl = "https://model-admin.crealitygroup.com"
        self.__overseaurl = "https://model-admin2.creality.com"
        self.__headers = {
            "__CXY_OS_VER_": "v0.0.1",
            "_CXY_OS_LANG_": "1",
            "__CXY_PLATFORM_": "5",
            "__CXY_DUID_": "234",
            "__CXY_APP_ID_": "creality_model",
            "__CXY_REQUESTID_": self._getQrandData(),
        }

    def _getQrandData(self):
        import time

        time = time.localtime(time.time())
        r = random.random() % (99999 - 10000) + 10000
        return "Raspberry" + str(time.tm_sec) + str(10) + str(r)  # time.tvm_usec

    def getconfig(slef,token):
        home_url = "https://model-admin.crealitygroup.com/api/cxy/v2/device/user/importDevice"
        oversea_url = "https://model-admin2.creality.com/api/cxy/v2/device/user/importDevice"
        headers = {
            "Content-Type": "application/json",
            "__CXY_JWTOKEN_": token
        }
        mac=uuid.UUID(int = uuid.getnode()).hex[-12:].upper()
        data = '{"mac": "' + str(mac) + '"}'
        response = requests.post(home_url, data=data, headers=headers, timeout=2).text
        if "result" not in response:
            response = requests.post(oversea_url, data=data, headers=headers, timeout=2).text
        res = json.loads(response)
        return res

    def getAddrress1(self):
        url = self.__homeurl + "/api/cxy/v2/common/getAddrress"
        response = requests.post(url, data="{}", headers=self.__headers, timeout=2).text
        res = json.loads(response)
        if res["code"] == 0:
            if res["result"]["apiUrl"] != None:
                return (res["result"]["apiUrl"], res["result"]["country"])
        return ("", "US")

    def getAddrress2(self):
        url = self.__overseaurl + "/api/cxy/v2/common/getAddrress"
        response = requests.post(url, data="{}", headers=self.__headers, timeout=2).text
        res = json.loads(response)
        if res["code"] == 0:
            if res["result"]["apiUrl"] != None:
                return (res["result"]["apiUrl"], res["result"]["country"])
        return ("", "US")
