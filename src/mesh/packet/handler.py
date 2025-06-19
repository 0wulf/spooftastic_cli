import logging
from datetime import datetime
from typing import Any, Dict, Optional
from meshtastic.protobuf import mqtt_pb2, mesh_pb2, portnums_pb2, telemetry_pb2
from src.db import DB
from src.mesh.encryption import decrypt_packet
from src.utils import num_to_id, num_to_mac, id_to_num, hw_num_to_model

def handle_nodeinfo(payload: bytes) -> Dict[str, Any]:
    user = mesh_pb2.User()
    user.ParseFromString(payload)
    hw_model_n = getattr(user, 'hw_model', None)
    hw_model = hw_num_to_model(hw_model_n)
    node_num = id_to_num(user.id)
    macaddr = num_to_mac(node_num)
    pubkey = user.public_key.hex() if user.public_key else None
    logging.info(f"[NodeInfo] node_num={node_num}, node_id={user.id}, macaddr={macaddr}, long_name={user.long_name}, short_name={user.short_name}, hw_model={hw_model}, public_key={pubkey}")
    return {
        'long_name': user.long_name,
        'short_name': user.short_name,
        'hw_model': hw_model_n,
        "pubkey": pubkey,
    }

def handle_position(payload: bytes) -> Dict[str, Any]:
    pos = mesh_pb2.Position()
    pos.ParseFromString(payload)
    logging.info(f"[Position] lat={pos.latitude_i/1e7}, lon={pos.longitude_i/1e7}, alt={pos.altitude}, time={pos.time}")
    return {
        'lat': pos.latitude_i / 1e7,
        'lon': pos.longitude_i / 1e7,
        'alt': pos.altitude
    }

def handle_range_test(payload: bytes) -> None:
    logging.info(f"[RangeTest] payload={payload}")

def handle_telemetry(payload: bytes) -> None:
    telemetry = telemetry_pb2.Telemetry()
    try:
        telemetry.ParseFromString(payload)
        logging.debug(f"[Telemetry] {telemetry}")
        logging.info(f"[Telemetry] temperature={getattr(telemetry, 'temperature', None)}, humidity={getattr(telemetry, 'relative_humidity', None)}, pressure={getattr(telemetry, 'barometric_pressure', None)}")
    except Exception as e:
        logging.warning(f"[Telemetry] failed to decode: {e}")

def handle_route_discovery(payload: bytes) -> None:
    route_discovery = mesh_pb2.RouteDiscovery()
    try:
        route_discovery.ParseFromString(payload)
        logging.info(f"[RouteDiscovery] route={route_discovery.route}")
        logging.info(f"[RouteDiscovery] {route_discovery}")
    except Exception as e:
        logging.warning(f"[RouteDiscovery] failed to decode: {e}")

def handle_routing(payload: bytes) -> None:
    routing = mesh_pb2.Routing()
    try:
        routing.ParseFromString(payload)
        logging.info(f"[Routing] routing={routing}")
    except Exception as e:
        logging.warning(f"[Routing] failed to decode: {e}")

def handle_other(portnum: int, payload: bytes) -> None:
    logging.info(f"[Other] portnum={portnum} payload={payload}")

def handle_packet(
    packet: mesh_pb2.MeshPacket,
    decoded_data: mesh_pb2.Data,
    enabled_portnums: Optional[list] = None,
    callback: Optional[callable] = None
) -> None:
    if enabled_portnums is None:
        logging.warning("No enabled portnums provided, processing all packets.")

    from_node_number = getattr(packet, 'from', 0)
    to_node_number = getattr(packet, 'to', 0)
    from_node_id = num_to_id(from_node_number)
    to_node_id = num_to_id(to_node_number)
    from_node_shortname, from_node_longname = DB.resolve_node_names(from_node_number)
    to_node_shortname, to_node_longname = DB.resolve_node_names(to_node_number)
    portnum = portnums_pb2.PortNum.Name(decoded_data.portnum) if decoded_data.portnum in portnums_pb2.PortNum.values() else decoded_data.portnum

    if enabled_portnums is not None and decoded_data.portnum not in enabled_portnums:
        logging.debug(f"[Packet] Port number {decoded_data.portnum} not enabled, skipping processing.")
        return
    logging.info(f"[Packet] from: {from_node_number} ({from_node_id}, {from_node_shortname}, {from_node_longname}) >-- portnum:{portnum} --> to: {to_node_number} ({to_node_id}, {to_node_shortname}, {to_node_longname})")
    logging.debug(f"[Packet] decoded={decoded_data}")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    node_kwargs = dict()
    match decoded_data.portnum:
        case portnums_pb2.NODEINFO_APP:
                node_kwargs = handle_nodeinfo(decoded_data.payload)
        case portnums_pb2.POSITION_APP:
                node_kwargs = handle_position(decoded_data.payload)
        case portnums_pb2.RANGE_TEST_APP:
                handle_range_test(decoded_data.payload)
        case portnums_pb2.TELEMETRY_APP:
                handle_telemetry(decoded_data.payload)
        case portnums_pb2.TRACEROUTE_APP:
                handle_route_discovery(decoded_data.payload)
        case portnums_pb2.ROUTING_APP:
                handle_routing(decoded_data.payload)
        case portnums_pb2.TEXT_MESSAGE_APP:
                logging.info(f"[TextMessage] {decoded_data.payload.decode('utf-8', errors='ignore')}")
        case _:
                handle_other(decoded_data.portnum, decoded_data.payload)
    DB.add_or_update_node(
        node_number=from_node_number,
        last_seen=now,
        **node_kwargs
    )

    if callback is not None:
        try:
            callback(packet, decoded_data, decoded_data.portnum, from_node_id, to_node_id, **node_kwargs)
        except Exception as e:
            logging.error(f"Error in callback: {e}")



def _should_process_packet(packet, node_id=None, enabled_portnums=None):
    from_ = num_to_id(getattr(packet, 'from', None))
    if node_id is not None and from_ != node_id:
        return False
    portnum = None
    if packet.HasField('decoded'):
        portnum = packet.decoded.portnum
    elif packet.HasField('encrypted'):
        pass
    if enabled_portnums is not None and portnum is not None and portnum not in enabled_portnums:
        return False
    return True

def on_message(client, userdata, msg, key: Optional[str] = None, enabled_portnums: Optional[list] = None, callback = None) -> None:
    try:
        envelope = mqtt_pb2.ServiceEnvelope()
        envelope.ParseFromString(msg.payload)
        if envelope.HasField('packet'):
            packet = envelope.packet
            logging.debug(f"Received packet:\n{packet}")
            if packet.HasField('decoded'):
                handle_packet(packet, packet.decoded, enabled_portnums, callback=callback)
            elif packet.HasField('encrypted'):
                pki_encrypted = getattr(packet, 'pki_encrypted', False)
                from_ = getattr(packet, 'from')
                from_id = num_to_id(from_)
                from_shortname, from_longname = DB.resolve_node_names(from_)
                to_id = num_to_id(packet.to)
                to_shortname, to_longname = DB.resolve_node_names(packet.to)
                if not pki_encrypted:
                    if key is not None:
                        payload = decrypt_packet(packet, key)
                        if payload is not None:
                            handle_packet(packet, payload, enabled_portnums, callback=callback)
                        else:
                            logging.info(f"[Encrypted] Could not decrypt packet from {from_} ({from_id}, {from_shortname}, {from_longname}) to {packet.to} ({to_id}, {to_shortname}, {to_longname})")
                            logging.debug(f"Packet:\n{packet}")
                    else:
                        logging.info(f"[Encrypted] No key provided for decryption.")
                else:
                    logging.info(f"[PKI] Trying to decrypt PKI encrypted packet from {from_} ({from_id}, {from_shortname}, {from_longname}) to {packet.to} ({to_id}, {to_shortname}, {to_longname}) (Not implemented yet)")
                    
    except Exception as e:
        logging.info(f"Error parsing message: {e}")

def filtered_on_message_factory(node_id=None, callback=None, enabled_portnums=None, key=None):
    def handler(client, userdata, msg):
        envelope = mqtt_pb2.ServiceEnvelope()
        try:
            envelope.ParseFromString(msg.payload)
            if envelope.HasField('packet'):
                packet = envelope.packet
                if not _should_process_packet(packet, node_id=node_id, enabled_portnums=enabled_portnums):
                    from_ = num_to_id(getattr(packet, 'from', None))
                    to = num_to_id(getattr(packet, 'to', None))
                    logging.debug(f"Filtered out packet from {from_} () to {to} ()")
                    return
            
                on_message(client, userdata, msg, key, enabled_portnums=enabled_portnums, callback=callback)
        except Exception as e:
            logging.info(f"Sniffer: Error in filtered_on_message: {e}")
    return handler
