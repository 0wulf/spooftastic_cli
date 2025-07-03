import paho.mqtt.client as mqtt
import ssl

class MqttBrokerClient:
    def __init__(self, broker, port, username, password, client_id="", on_connect=None, tls=False, ca_certs=None):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.tls = tls
        self.ca_certs = ca_certs
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, clean_session=True, userdata=None)
        if on_connect:
            self.client.on_connect = on_connect
        self.tls_configured = False
        self.connected = False

    def connect(self, key=None, debug=False, set_topic_fn=None, publish_topic=None):
        self.client.username_pw_set(self.username, self.password)
        if self.tls and not self.tls_configured:
            self.client.tls_set(ca_certs=self.ca_certs, tls_version=ssl.PROTOCOL_TLSv1_2)
            self.client.tls_insecure_set(False)
            self.tls_configured = True
        if key is not None and key == "AQ==":
            if debug:
                print("key is default, expanding to AES128")
            key = "1PG7OiApB1nwvP+rz05pAQ=="
        if key is not None:
            padded_key = key.ljust(len(key) + ((4 - (len(key) % 4)) % 4), '=')
            replaced_key = padded_key.replace('-', '+').replace('_', '/')
            key = replaced_key
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()
        self.connected = True
        if set_topic_fn:
            set_topic_fn()
        if debug and publish_topic:
            print(f"Connected to server: {self.broker}")
            print(f"Publish Topic is: {publish_topic}\n")

    def disconnect(self, debug=False):
        if self.is_connected():
            self.client.disconnect()
            self.connected = False
        if debug:
            print("Client Disconnected")

    def is_connected(self):
        return self.client.is_connected() if self.client else False

    def publish(self, topic, payload):
        self.client.publish(topic, payload)

    def set_on_connect(self, on_connect):
        self.client.on_connect = on_connect

def connect_and_get_client(mqtt_broker, mqtt_port, mqtt_username, mqtt_password, key, debug, set_topic_fn, publish_topic, client_id):
    tls = mqtt_port == 8883
    ca_certs = "cacert.pem" if tls else None
    mqtt_client = MqttBrokerClient(
        broker=mqtt_broker,
        port=mqtt_port,
        username=mqtt_username,
        password=mqtt_password,
        client_id=client_id,
        tls=tls,
        ca_certs=ca_certs
    )
    mqtt_client.connect(key=key, debug=debug, set_topic_fn=set_topic_fn, publish_topic=publish_topic)
    return mqtt_client

def disconnect_client(mqtt_client, debug=False):
    mqtt_client.disconnect(debug=debug)
