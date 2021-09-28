import json
import random

import requests


class CrealityAPI(object):
    def __init__(self):
        # self.__secret = "Os5juJJERoUosWpbd2Q4QmkpNRNr"
        # self.__g_secret = "dAmohq4DTBH4khjbH7S5Dl7l1FytYPv"
        self.__homeurl = "https://model-admin.crealitygroup.com"  # "https://model-admin.crealitygroup.com/api/cxy/v2/common/getAddrress"
        self.__overseaurl = "https://model-admin2.creality.com"  # "https://model-admin2.creality.com/api/cxy/v2/common/getAddrress"
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

    def getAddrress(self):
        url = self.__homeurl + "/api/cxy/v2/common/getAddrress"
        response = requests.post(url, data="{}", headers=self.__headers).text
        res = json.loads(response)
        if res["code"] == 0:
            if res["result"]["apiUrl"] != None:
                return (res["result"]["apiUrl"], res["result"]["country"])
