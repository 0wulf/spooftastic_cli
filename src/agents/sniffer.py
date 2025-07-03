import logging
import time
from src.clients.mqtt_client import connect_and_get_client, disconnect_client
from settings import MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, ROOT_TOPIC, CHANNEL, BROADCAST_MAC, CLIENT_ID
from src.utils import set_topic, ensure_aes_key
from src.mesh.packet.handler import filtered_on_message_factory

class Sniffer:
    """Encapsulates listen mode logic for Meshtastic MQTT packets."""
    def __init__(self, key=None, debug=False):
        self.key = ensure_aes_key(key)
        self.debug = debug
        self.mqtt_client = None
        self.publish_topic = set_topic(BROADCAST_MAC, ROOT_TOPIC, CHANNEL)

    def close(self):
        if self.mqtt_client:
            disconnect_client(self.mqtt_client, self.debug)
            self.mqtt_client = None

    def sniff(
            self,
            node_id=None,
            callback=None,
            enabled_portnums=None
    ):
        self.mqtt_client = connect_and_get_client(
            MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, self.key, self.debug, lambda: None, self.publish_topic, CLIENT_ID
        )
        topic = f"{ROOT_TOPIC}#"
        self.mqtt_client.client.subscribe(topic)
        logging.info(f"Sniffer: Subscribed to {topic} for node {node_id}.")
        self.mqtt_client.client.on_message = filtered_on_message_factory(
            node_id=node_id, callback=callback, enabled_portnums=enabled_portnums, key=self.key
        )
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            logging.info("Sniffer: Exiting node sniff.")
        self.close()

