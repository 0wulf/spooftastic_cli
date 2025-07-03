import time
import logging
from src.mesh.packet.crafter import send_position, send_message, send_node_info
from src.clients.mqtt_client import connect_and_get_client, disconnect_client
from src.utils import set_topic, hw_model_to_num
from settings import MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, ROOT_TOPIC, CHANNEL, KEY, DEBUG, CLIENT_ID

global_message_id = None

def handle_send_mode(args):
    global global_message_id
    if global_message_id is None:
        import random
        global_message_id = random.getrandbits(32)
    publish_topic = set_topic(args.gateway_node, ROOT_TOPIC, CHANNEL)
    mqtt_client = connect_and_get_client(
        MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, KEY, DEBUG, lambda: None, publish_topic, CLIENT_ID
    )
    time.sleep(1)
    if mqtt_client and mqtt_client.is_connected():
        if args.send_type == 'position':
            logging.info("Sending position...")
            send_position(
                args.to_node, args.lat, args.lon, args.alt, args.from_node, CHANNEL, KEY, global_message_id, args.from_node, publish_topic, mqtt_client, DEBUG
            )
        elif args.send_type == 'nodeinfo':
            logging.info("Sending nodeinfo...")
            short_name = args.short_name or ""
            long_name = args.long_name or ""
            send_node_info(
                args.to_node, True, args.from_node, CHANNEL, KEY, global_message_id,
                short_name, long_name, short_name,
                hw_model_to_num(args.hw_model), args.pubkey,
                publish_topic, mqtt_client, DEBUG
            )
        elif args.send_type == 'message':
            logging.info(f"Sending message: {args.message}")
            send_message(
                args.to_node, args.message, args.from_node, CHANNEL, KEY,
                global_message_id, args.from_node, publish_topic, mqtt_client, DEBUG
            )
        global_message_id += 1
    disconnect_client(mqtt_client, DEBUG)
