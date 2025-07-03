import argparse
from settings import BROADCAST_MAC, KEY

def build_parser():
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
    send_nodeinfo_parser.add_argument('--hw-model', type=str, help='Hardware model of the node')
    send_nodeinfo_parser.add_argument('--pubkey', type=str, help='Public key of the node', default=KEY)

    # Send message
    send_message_parser = send_subparsers.add_parser("message", help="Send a text message")
    send_message_parser.add_argument('--message', type=str, required=True, help='Message text to send')

    # DB subparser
    db_subparser = subparsers.add_parser("db", help="Database operations")
    db_subparser.add_argument('--follow', action='store_true', help='Continuously refresh the table output every second')
    db_subparsers = db_subparser.add_subparsers(dest="db_action", required=True, help="Database action")
    db_subparsers.add_parser("delete", help="Delete the database")

    # nodes subparser for db
    nodes_parser = db_subparsers.add_parser("nodes", help="Node operations")
    nodes_parser.add_argument('--sort', dest='sort', type=str, default='packets', help='Column to sort by (default: packets, descending)')
    nodes_subparsers = nodes_parser.add_subparsers(dest="nodes_action", required=True, help="Node action")
    nodes_subparsers.add_parser("list", help="List all nodes")
    nodes_subparsers.add_parser("position", help="List all nodes with positions")
    nodes_subparsers.add_parser("device", help="List all nodes with device metrics")
    nodes_subparsers.add_parser("environment", help="List all nodes with environment data")
    get_parser = nodes_subparsers.add_parser("get", help="Get node by MAC or number")
    get_parser.add_argument("node_id", type=str, help="Node id in the form !abcd1234")
    set_parser = nodes_subparsers.add_parser("set", help="Set a column value for a node")
    set_parser.add_argument("node_id", type=str, help="Node id in the form !abcd1234")
    set_parser.add_argument("column", type=str, help="Column to set")
    set_parser.add_argument("value", type=str, help="Value to set")
    packet_parser = nodes_subparsers.add_parser("packet", help="Show node packet metrics")
    packet_parser.add_argument("node_id", type=str, nargs="?", help="Node id in the form !abcd1234 (optional, if omitted shows all packets)")
    activity_parser = nodes_subparsers.add_parser("activity", help="Show node activity metrics for the last N minutes")
    activity_parser.add_argument("--last-minutes", dest="minutes", type=int, default=3600, help="Interval in minutes to calculate metrics (default: 3600, a day)")
    activity_parser.add_argument("node_id", type=str, nargs="?", help="Node id in the form !abcd1234 (optional, if omitted shows all nodes)")
    activity_parser.add_argument('--sort', dest='sort', type=str, default='Packets', help='Column to sort by (default: Packets, descending)')

    # channels subparser for db
    channels_parser = db_subparsers.add_parser("channels", help="Channel operations")
    channels_subparsers = channels_parser.add_subparsers(dest="channels_action", required=True, help="Channel action")
    channels_subparsers.add_parser("list", help="List all channels")
    show_parser = channels_subparsers.add_parser("show", help="Show channel info and members")
    show_parser.add_argument("channel_id", type=str, help="Channel name/id to show")
    activity_parser = channels_subparsers.add_parser("activity", help="Show channel activity (Packets, Bytes) for each channel")

    # Spoofer subparser
    spoofer_parser = subparsers.add_parser("spoofer", help="Spoof a node")
    spoofer_parser.add_argument('--gateway-node', type=str, default=BROADCAST_MAC, help='Gateway node mac to spoof data to')
    spoofer_parser.add_argument('--to-node', type=str, default=BROADCAST_MAC, help='Node mac to spoof data to')
    spoofer_parser.add_argument('--node-id', type=str, required=True, help='Node ID to spoof')
    spoofer_parser.add_argument('--short-name', type=str, help='Short name of the spoofed node')
    spoofer_parser.add_argument('--long-name', type=str, help='Long name of the spoofed node')
    spoofer_parser.add_argument('--hw-model', type=str, help='Hardware model of the spoofed node. Example: HELTEC_V3')
    spoofer_parser.add_argument('--lat', type=float, help='Latitude of the spoofed node')
    spoofer_parser.add_argument('--lon', type=float, help='Longitude of the spoofed node')
    spoofer_parser.add_argument('--alt', type=float, help='Altitude of the spoofed node')
    spoofer_parser.add_argument('--burst', type=int, default=1, help='Number of spoof packets to send per event (reactive mode)')
    spoofer_parser.add_argument('--period', type=float, default=2, help='Seconds between spoof packets in a burst (reactive mode)')
    spoofer_parser.add_argument('--restore-after', action='store_true', help='(Placeholder) Restore original node info after spoofing (currently not implemented)')
    spoof_mode_subparsers = spoofer_parser.add_subparsers(dest="spoof_mode", help="Type of spoofing")
    reactive_spoofing_parser = spoof_mode_subparsers.add_parser("reactive", help="Spoof node when receiving nodeinfo/position from the original node")
    periodic_spoofing_parser = spoof_mode_subparsers.add_parser("periodic", help="Spoof node periodically")
    periodic_spoofing_parser.add_argument('--interval', type=int, default=60, help='Interval in seconds for periodic spoofing')
    hybrid_spoofing_parser = spoof_mode_subparsers.add_parser("hybrid", help="Spoof node periodically and when receiving nodeinfo/position from the original node")
    hybrid_spoofing_parser.add_argument('--interval', type=int, default=60, help='Interval in seconds for periodic spoofing')
    return parser
