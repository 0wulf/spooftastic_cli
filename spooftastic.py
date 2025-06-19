import random
import time
import logging
import argparse
import ast

from meshtastic.protobuf import portnums_pb2

from settings import MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, ROOT_TOPIC, CHANNEL, KEY, DEBUG, BROADCAST_MAC
from src.mesh.packet.crafter import send_position, send_message, send_node_info
from src.mqtt_client import connect_and_get_client, disconnect_client
from src.utils import set_topic
from src.sniffer import Sniffer
from src.db import DB
from src.spoofer import Spoofer



logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
global_message_id = random.getrandbits(32)


def handle_sniffer_mode(args):
    """Start sniffer with selected portnums from argparse args."""
    portnums = []
    if getattr(args, 'text', False):
        portnums.append(portnums_pb2.TEXT_MESSAGE_APP)
    if getattr(args, 'seq', False):
        portnums.append(portnums_pb2.RANGE_TEST_APP)
    if getattr(args, 'position', False):
        portnums.append(portnums_pb2.POSITION_APP)
    if getattr(args, 'nodeinfo', False):
        portnums.append(portnums_pb2.NODEINFO_APP)
    if getattr(args, 'route', False):
        portnums.extend([portnums_pb2.TRACEROUTE_APP, portnums_pb2.ROUTING_APP])
    if getattr(args, 'telemetry', False):
        portnums.append(portnums_pb2.TELEMETRY_APP)
    if not portnums:
        portnums = [
            portnums_pb2.TEXT_MESSAGE_APP,
            portnums_pb2.RANGE_TEST_APP,
            portnums_pb2.POSITION_APP,
            portnums_pb2.NODEINFO_APP,
            portnums_pb2.TRACEROUTE_APP,
            portnums_pb2.ROUTING_APP,
            portnums_pb2.TELEMETRY_APP
        ]

    sniffer = Sniffer(key=getattr(args, 'key', None), debug=getattr(args, 'debug', False))
    sniffer.sniff(enabled_portnums=portnums)


def handle_send_mode(args):
    publish_topic = set_topic(args.gateway_node, ROOT_TOPIC, CHANNEL)
    mqtt_client = connect_and_get_client(
        MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, KEY, DEBUG, lambda: None, publish_topic
    )
    time.sleep(1)
    global global_message_id
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
                args.hw_model, args.pubkey,
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


def handle_db_mode(args):
    db = DB
    if getattr(args, 'db_action', None) == 'nodes':
        if args.nodes_action == 'list':
            logging.info("Listing all nodes from the database...")
            nodes = db.get_all_nodes()
            for node in nodes:
                logging.info(
                    f"Node Number: {node.node_number}, Node ID: {node.node_id}, MAC: {node.node_mac}, Short Name: {node.short_name}, Long Name: {node.long_name}, "
                    f"Lat: {node.lat}, Lon: {node.lon}, Alt: {node.alt}, HW Model: {node.hw_model}, Pubkey: {getattr(node, 'pubkey', None)}, Freeze: {getattr(node, 'freeze', False)}"
                )
        elif args.nodes_action == 'get':
            node_id = args.node_id
            node = None

            try:
                node_number = int(node_id)
                node = db.get_node(node_number)
            except ValueError:
                for n in db.get_all_nodes():
                    if n.node_mac == node_id:
                        node = n
                        break
            if node:
                logging.info(f"Node: {node.node_number}, MAC: {node.node_mac}, Short Name: {node.short_name}, Long Name: {node.long_name}, "
                    f"Lat: {node.lat}, Lon: {node.lon}, Alt: {node.alt}, HW Model: {node.hw_model}, Pubkey: {getattr(node, 'pubkey', None)}, Freeze: {getattr(node, 'freeze', False)}")
            else:
                logging.info(f"Node not found: {node_id}")
        elif args.nodes_action == 'set':
            node_id = args.node_id
            column = args.column
            value = args.value
            node = None

            try:
                node_number = int(node_id)
                node = db.get_node(node_number)
            except ValueError:
                for n in db.get_all_nodes():
                    if n.node_mac == node_id:
                        node = n
                        break
            if not node:
                logging.info(f"Node not found: {node_id}")
                return

            valid_columns = set(node.__dict__.keys())
            if column not in valid_columns:
                logging.info(f"Invalid column: {column}")
                return
            # Convert value to correct type
            try:
                if column in ['lat', 'lon', 'alt', 'temperature', 'relative_humidity', 'barometric_pressure', 'voltage', 'battery_level', 'rssi', 'snr']:
                    value = float(value)
                elif column in ['node_number']:
                    value = int(value)
                elif column in ['freeze']:
                    value = value.lower() in ['1', 'true', 'yes', 'on']
            except Exception:
                pass
            # If freeze is set and not updating freeze, block and inform user
            if getattr(node, 'freeze', False) and column != 'freeze':
                logging.info(f"Node {node_id} is frozen. Only the 'freeze' column can be modified until it is unset.")
                return
            # Call add_or_update_node with only the column to update
            kwargs = dict(node_number=node.node_number)
            for k in valid_columns:
                if k != 'id':
                    kwargs[k] = getattr(node, k)
            # Ensure value is str or int for kwargs assignment
            if isinstance(value, (float, bool)):
                kwargs[column] = value
            else:
                try:
                    kwargs[column] = ast.literal_eval(value)
                except Exception:
                    kwargs[column] = value
            db.add_or_update_node(**kwargs)
            logging.info(f"Set {column} to {value} for node {node_id}")
    elif getattr(args, 'db_action', None) == 'show-nodes':
        logging.info("Showing nodes from the database...")
        nodes = db.get_all_nodes()
        for node in nodes:
            logging.info(
                f"Node: {node.node_number}, MAC: {node.node_mac}, Short Name: {node.short_name}, Long Name: {node.long_name}, "
                f"Lat: {node.lat}, Lon: {node.lon}, Alt: {node.alt}, HW Model: {node.hw_model}, Pubkey: {getattr(node, 'pubkey', None)}"
            )
    elif getattr(args, 'db_action', None) == 'delete':
        logging.info("Deleting the database...")
        db.delete_database()


def handle_spoofer_mode(args):
    spoofer = Spoofer()
    spoof_mode = getattr(args, 'spoof_mode', None)
    # Pass all CLI params for spoofable fields
    kwargs = dict(
        to_node=args.to_node,
        from_node=args.node_id,
        short_name=getattr(args, 'short_name', None),
        long_name=getattr(args, 'long_name', None),
        hw_model=getattr(args, 'hw_model', None),
        lat=getattr(args, 'lat', None),
        lon=getattr(args, 'lon', None),
        alt=getattr(args, 'alt', None),
        pubkey=getattr(args, 'pubkey', None),
        gateway_node=getattr(args, 'gateway_node', BROADCAST_MAC),
        burst=getattr(args, 'burst', 1),
        period=getattr(args, 'period', 2),
        restore_after=getattr(args, 'restore_after', False),
    )
    if spoof_mode == 'reactive':
        spoofer.spoof_reactive(**kwargs)
    elif spoof_mode == 'periodic':
        interval = getattr(args, 'interval', 60)
        spoofer.spoof_periodic(**kwargs, interval=interval)
    elif spoof_mode == 'hybrid':
        interval = getattr(args, 'interval', 60)
        spoofer.spoof_hybrid(**kwargs, interval=interval)
    else:
        spoofer.spoof_node(**kwargs)


def main():
    parser = argparse.ArgumentParser(description="Meshtastic MQTT Client")
    subparsers = parser.add_subparsers(dest="mode", required=True, help="Mode of operation")
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    # sniffer subparser
    sniffer_parser = subparsers.add_parser("sniffer", help="sniffer for incoming packets")
    sniffer_parser.add_argument('--text', action='store_true', help='Print incoming text messages')
    sniffer_parser.add_argument('--seq', action='store_true', help='Print incoming sequence numbers')
    sniffer_parser.add_argument('--position', action='store_true', help='Print incoming position data')
    sniffer_parser.add_argument('--nodeinfo', action='store_true', help='Print incoming nodeinfo data')
    sniffer_parser.add_argument('--route', action='store_true', help='Print incoming routing data')
    sniffer_parser.add_argument('--telemetry', action='store_true', help='Print incoming telemetry data')

    # Send subparser with its own subparsers
    send_parser = subparsers.add_parser("send", help="Send data (position, nodeinfo, message)")
    send_subparsers = send_parser.add_subparsers(dest="send_type", required=True, help="Type of data to send")
    send_parser.add_argument('--gateway-node', type=str, default=BROADCAST_MAC, help='Gateway node mac to send data to')
    send_parser.add_argument('--to-node', type=str, default=BROADCAST_MAC, help='Node mac to send data to')
    send_parser.add_argument('--from-node', type=str, help='Node mac sending the data')

    # Send position
    send_position_parser = send_subparsers.add_parser("position", help="Send position data")
    send_position_parser.add_argument('--lat', type=float, help='Latitude of the position')
    send_position_parser.add_argument('--lon', type=float, help='Longitude of the position')
    send_position_parser.add_argument('--alt', type=float, help='Altitude of the position')

    # Send nodeinfo
    send_nodeinfo_parser = send_subparsers.add_parser("nodeinfo", help="Send nodeinfo data")
    send_nodeinfo_parser.add_argument('--short-name', type=str, help='Short name of the node')
    send_nodeinfo_parser.add_argument('--long-name', type=str, help='Long name of the node')
    send_nodeinfo_parser.add_argument('--hw-model', type=int, help='Hardware model of the node')
    send_nodeinfo_parser.add_argument('--pubkey', type=str, help='Public key of the node', default=KEY)

    # Send message
    send_message_parser = send_subparsers.add_parser("message", help="Send a text message")
    send_message_parser.add_argument('--message', type=str, required=True, help='Message text to send')

    # DB subparser
    db_subparser = subparsers.add_parser("db", help="Database operations")
    db_subparsers = db_subparser.add_subparsers(dest="db_action", required=True, help="Database action")

    # nodes subparser for db
    nodes_parser = db_subparsers.add_parser("nodes", help="Node operations")
    nodes_subparsers = nodes_parser.add_subparsers(dest="nodes_action", required=True, help="Node action")
    nodes_subparsers.add_parser("list", help="List all nodes")
    get_parser = nodes_subparsers.add_parser("get", help="Get node by MAC or number")
    get_parser.add_argument("node_id", type=str, help="Node MAC or number")
    set_parser = nodes_subparsers.add_parser("set", help="Set a column value for a node")
    set_parser.add_argument("node_id", type=str, help="Node MAC or number")
    set_parser.add_argument("column", type=str, help="Column to set")
    set_parser.add_argument("value", type=str, help="Value to set")

    # Spoofer subparser
    spoofer_parser = subparsers.add_parser("spoofer", help="Spoof a node")
    spoofer_parser.add_argument('--gateway-node', type=str, default=BROADCAST_MAC, help='Gateway node mac to spoof data to')
    # spoofer_parser.add_argument('--from-node', type=str, help='Node mac spoofing the data')
    spoofer_parser.add_argument('--to-node', type=str, default=BROADCAST_MAC, help='Node mac to spoof data to')
    spoofer_parser.add_argument('--node-id', type=str, required=True, help='Node ID to spoof')
    spoofer_parser.add_argument('--short-name', type=str, help='Short name of the spoofed node')
    spoofer_parser.add_argument('--long-name', type=str, help='Long name of the spoofed node')
    spoofer_parser.add_argument('--hw-model', type=int, help='Hardware model of the spoofed node. 43 for Heltec V3')
    spoofer_parser.add_argument('--lat', type=float, help='Latitude of the spoofed node')
    spoofer_parser.add_argument('--lon', type=float, help='Longitude of the spoofed node')
    spoofer_parser.add_argument('--alt', type=float, help='Altitude of the spoofed node')
    # spoofer_parser.add_argument('--pubkey', type=str, help='Public key of the spoofed node', default=KEY)
    spoofer_parser.add_argument('--burst', type=int, default=1, help='Number of spoof packets to send per event (reactive mode)')
    spoofer_parser.add_argument('--period', type=float, default=2, help='Seconds between spoof packets in a burst (reactive mode)')
    spoofer_parser.add_argument('--restore-after', action='store_true', help='Restore original node info after spoofing')

    spoof_mode_subparsers = spoofer_parser.add_subparsers(dest="spoof_mode", help="Type of spoofing")
    reactive_spoofing_parser = spoof_mode_subparsers.add_parser("reactive", help="Spoof node when receiving nodeinfo/position from the original node")
    periodic_spoofing_parser = spoof_mode_subparsers.add_parser("periodic", help="Spoof node periodically")
    periodic_spoofing_parser.add_argument('--interval', type=int, default=60, help='Interval in seconds for periodic spoofing')
    hybrid_spoofing_parser = spoof_mode_subparsers.add_parser("hybrid", help="Spoof node periodically and when receiving nodeinfo/position from the original node")
    hybrid_spoofing_parser.add_argument('--interval', type=int, default=60, help='Interval in seconds for periodic spoofing')
    

    args = parser.parse_args()
    global DEBUG
    DEBUG = args.debug
    logging.getLogger().setLevel(logging.DEBUG if DEBUG else logging.INFO)

    match args.mode:
        case 'sniffer':
            handle_sniffer_mode(args)
        case 'send':
            handle_send_mode(args)
        case 'db':
            handle_db_mode(args)
        case 'spoofer':
            handle_spoofer_mode(args)


if __name__ == "__main__":
    main()