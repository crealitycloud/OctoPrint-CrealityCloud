from aliyun_iot_device.mqtt import Client as IOT
import time

class CrealityCloud(object):

    def __init__(self,pk,dn,ds):
       
        self.iot = IOT(pk, dn, ds)

        self.iot.on_connect = self.on_connect
        self.iot.on_message = self.on_message

        self.iot.connect()

        self.iot.loop_start()
    def on_connect(client, userdata, flags, rc):
        print('subscribe')
        client.subscribe(qos=1)


    def on_message(client, userdata, msg):
        print('receive message')
        print(str(msg.payload))

    def on_event(self, state, continue_code="complete"):
        if state == 0:
            self.iot.publish(payload="success", qos=1)
        if state == 1:
            self.iot.publish(payload="success", qos=1)
        if state == 2:
            self.iot.publish(payload="success", qos=1)