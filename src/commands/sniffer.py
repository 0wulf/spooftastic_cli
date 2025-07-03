import logging
from meshtastic.protobuf import portnums_pb2
from src.agents.sniffer import Sniffer
from src.clients.db_client import update_channel_membership_callback

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
    sniffer.sniff(enabled_portnums=portnums, callback=update_channel_membership_callback)
