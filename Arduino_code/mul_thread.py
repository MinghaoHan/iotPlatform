import paho.mqtt.client as mqtt
import serial.tools.list_ports
import threading
import queue
import json
import time


class MQTTThread(threading.Thread):
    def __init__(self, threadID, name, host, port, username, password, topics):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.topics = topics
        self.init_mqtt()

    def run(self):
        print("Running " + self.name)
        client.loop_forever()
        print("Exiting " + self.name)

    def init_mqtt(self):
        def on_connect(client, userdata, flags, rc):
            print("Connected with result code "+str(rc))

        def on_message(client, userdata, msg):
            print("Topic:"+msg.topic+" Content:"+str(msg.payload.decode('utf-8')))
            process_data(str(msg.payload.decode('utf-8')))

        def on_subscribe(client, userdata, mid, granted_qos):
            print("On Subscribed: qos = %d" % granted_qos)

        def on_disconnect(client, userdata, rc):
            if rc != 0:
                print("Unexpected disconnection %s" % rc)

        client.username_pw_set(self.username, self.password)
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_subscribe = on_subscribe
        client.on_disconnect = on_disconnect
        client.connect(self.host, self.port, 60)
        for topic in self.topics:
            self.add_topic(topic)

    def add_topic(self, topic):
        client.subscribe(topic)
        print(topic)

    def send(self, topic, data):
        client.publish(topic, data)


class SerialThread(threading.Thread):
    def __init__(self, threadID, name, com_name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.com_name = com_name
        self.arduino_serial = self.init_serial()

    def run(self):
        print("Running " + self.name)
        while not EXIT_FLAG:
            res = self.arduino_serial.readline().strip()
            publish_data(res)
        print("Exiting " + self.name)

    def init_serial(self):
        plist = list(serial.tools.list_ports.comports())
        is_found = False
        for s in plist:
            if list(s)[0] == self.com_name:
                is_found = True
        if not is_found:
            print("Can not find any usable port!")
            return
        serialFd = serial.Serial(self.com_name, 9600, timeout=60)
        print("Connected to port", serialFd.name)
        return serialFd

    def write(self, data):
        self.arduino_serial.write(data + b'\n')


def process_data(content):
    try:
        content = json.loads(content.encode('utf-8'))[0]
    except Exception:
        content = json.loads(content.encode('utf-8'))
    global face_read
    global face_flag
    global temp_read
    global temp_flag
    try:
        if content['type'] == 'face':   # face_rec
            face_read = True
            face_flag = int(content['flag'])
            face_flag += 5
    except Exception:
        temp_read = True
        try:
            temp_flag = int(content['one'])
        except Exception:
            temp_flag = int(content['zero'])
    # if content['type'] == 'face':   # face_rec
    #     face_read = True
    #     face_flag = int(content['flag'])
    #     face_flag += 5
    # elif content['type'] == 'temp':  # dht11
    #     temp_read = True
    #     try:
    #         temp_flag = int(content['one'])
    #     except Exception:
    #         temp_flag = int(content['zero'])
    if face_read and temp_read:
        content1 = str(face_flag)
        content2 = str(temp_flag)
        print('now write f t', content1, content2)
        serial_thread.write(content1.encode('utf-8'))
        serial_thread.write(content2.encode('utf-8'))
        face_read = False
        temp_read = False
        face_flag = -2
        temp_flag = -2


def publish_data(res):
    try:
        content = {'temperature': int(res), 'type': 'temp', 'one': 1, 'zero': 0}
        content = json.dumps(content)
        mqtt_thread.send(TOPIC_PUB[0], content)
    except Exception:
        print('publish failed, check data format')


EXIT_FLAG = False
HOST = "106.15.88.231"
PORT = 1883
USERNAME = 'admin'
PASSWORD = 'public'
TOPIC_PUB = ['DataTopic_Temp']
TOPIC_SUB = ['CmdTopic_Arduino']
client = mqtt.Client()
face_read = False
temp_read = False
face_flag = -2
temp_flag = -2

mqtt_thread = MQTTThread(1, 'MQTT', HOST, PORT, USERNAME, PASSWORD, TOPIC_SUB)
serial_thread = SerialThread(2, 'Serial Communication', 'COM3')
mqtt_thread.start()
serial_thread.start()

while not EXIT_FLAG:
    flag = input('Input \'q\' to exit\n')
    if flag == 'q':
        EXIT_FLAG = True

client.disconnect()
mqtt_thread.join()
serial_thread.join()
