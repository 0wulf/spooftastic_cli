import logging
from datetime import datetime
from typing import Any, Dict, Optional
from meshtastic.protobuf import mqtt_pb2, mesh_pb2, portnums_pb2, telemetry_pb2
from src.clients.db_client import DB
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
        if telemetry.HasField('device_metrics'):
            device_metrics = telemetry.device_metrics
            voltage = round(device_metrics.voltage, 2) if device_metrics.voltage else None
            channel_utilization = round(device_metrics.channel_utilization, 2) if device_metrics.channel_utilization else None
            air_util_tx = round(device_metrics.air_util_tx, 2) if device_metrics.air_util_tx else None
            logging.info(f"[Telemetry] device_metrics: battery_level={device_metrics.battery_level}, voltage={voltage}, channel_utilization={channel_utilization}, air_util_tx={air_util_tx}, uptime_seconds={device_metrics.uptime_seconds}")
            return {
                'battery_level': device_metrics.battery_level,
                'voltage': voltage,
                'channel_utilization': channel_utilization,
                'air_util_tx': air_util_tx,
                'uptime_seconds': device_metrics.uptime_seconds
            }
    
        if telemetry.HasField('environment_metrics'):
            env_metrics = telemetry.environment_metrics
            temperature = round(env_metrics.temperature, 2) if env_metrics.temperature else None
            relative_humidity = round(env_metrics.relative_humidity, 2) if env_metrics.relative_humidity else None
            barometric_pressure = round(env_metrics.barometric_pressure, 2) if env_metrics.barometric_pressure else None
            gas_resistance = round(env_metrics.gas_resistance, 2) if env_metrics.gas_resistance else None
            iaq = round(env_metrics.iaq, 2) if env_metrics.iaq else None
            logging.info(f"[Telemetry] environment_metrics: temperature={temperature}, relative_humidity={relative_humidity}, barometric_pressure={barometric_pressure}, gas_resistance={gas_resistance}, iaq={iaq}")
            return {
                'temperature': temperature,
                'relative_humidity': relative_humidity,
                'barometric_pressure': barometric_pressure,
                'gas_resistance': gas_resistance,
                'iaq': iaq
            }
        
        return 
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
    callback: Optional[callable] = None,
    gateway_node_id: Optional[str] = None,
    channel_id_str: Optional[str] = None  # Pass the human-readable channel id
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
                node_kwargs = handle_telemetry(decoded_data.payload)
        case portnums_pb2.TRACEROUTE_APP:
                handle_route_discovery(decoded_data.payload)
        case portnums_pb2.ROUTING_APP:
                handle_routing(decoded_data.payload)
                # --- ACK-matching logic for packet success ---
                try:
                    routing = mesh_pb2.Routing()
                    routing.ParseFromString(decoded_data.payload)
                    # Try to extract request_id from multiple sources
                    request_id = getattr(routing, 'request_id', None)
                    # Fallback: try decoded_data.request_id if present
                    if (request_id is None or request_id == 0) and hasattr(decoded_data, 'request_id'):
                        request_id = getattr(decoded_data, 'request_id', None)
                        logging.debug(f"[ACK-DEBUG] Fallback: got request_id from decoded_data: {request_id}")
                    # Fallback: try to parse payload as Routing and get request_id
                    if (request_id is None or request_id == 0):
                        try:
                            routing2 = mesh_pb2.Routing()
                            routing2.ParseFromString(decoded_data.payload)
                            request_id = getattr(routing2, 'request_id', None)
                            logging.debug(f"[ACK-DEBUG] Fallback: got request_id from reparsed payload: {request_id}")
                        except Exception as e:
                            logging.debug(f"[ACK-DEBUG] Could not extract request_id from payload: {e}")
                    logging.debug(f"[ACK-DEBUG] RoutingApp received: error_reason={getattr(routing, 'error_reason', None)}, request_id={request_id}, from_node_id={from_node_id}, to_node_id={to_node_id}")
                    # Only care about error_reason==NONE and request_id: mark by request_id only
                    if hasattr(routing, 'error_reason') and routing.error_reason == 0 and request_id not in (None, 0):
                        logging.debug(f"[ACK-DEBUG] Attempting to mark packet_id={request_id} as success=True (ANY node)")
                        updated = DB.mark_packet_success_by_ack(request_id=request_id)
                        if updated:
                            logging.info(f"[ACK] Marked packet_id={request_id} as success=True (ANY node)")
                        else:
                            logging.warning(f"[ACK-DEBUG] No matching NodePacket found for packet_id={request_id} (ANY node)")
                    else:
                        logging.debug(f"[ACK-DEBUG] RoutingApp packet did not meet ACK criteria: error_reason={getattr(routing, 'error_reason', None)}, request_id={request_id}")
                except Exception as e:
                    logging.warning(f"[ACK] Failed to process RoutingApp ACK: {e}")
        case portnums_pb2.TEXT_MESSAGE_APP:
                logging.info(f"[TextMessage] {decoded_data.payload.decode('utf-8', errors='ignore')}")
        case _:
                handle_other(decoded_data.portnum, decoded_data.payload)
    DB.add_or_update_node(
        node_number=from_node_number,
        last_seen=now,
        **node_kwargs
    )

    # Guardar actividad del nodo
    try:
        # Determinar gateway_node_id (node_id en el topic MQTT)
        gateway_node_dbid = None
        if gateway_node_id:
            from src.models import Node
            session = DB.get_session()
            try:
                node = session.query(Node).filter(Node.node_id == gateway_node_id).first()
                if node:
                    gateway_node_dbid = node.id
            finally:
                session.close()
        # Convertir node_number a node_id (string tipo !abcd1234) antes de guardar
        from_node_id_str = num_to_id(from_node_number)
        to_node_id_str = num_to_id(to_node_number)
        # --- NEW: get channel_id and packet_id, rx_rssi, rx_snr, rx_time, hop_start, hop_limit ---
        channel_id = channel_id_str  # Use the string from the envelope, not the hash
        packet_id = None
        rx_rssi = None
        rx_snr = None
        rx_time = None
        hop_start = None
        hop_limit = None
        try:
            if hasattr(packet, 'id'):
                packet_id = getattr(packet, 'id', None)
            if hasattr(packet, 'rx_rssi'):
                rx_rssi = getattr(packet, 'rx_rssi', None)
            if hasattr(packet, 'rx_snr'):
                rx_snr = getattr(packet, 'rx_snr', None)
            if hasattr(packet, 'rx_time'):
                rx_time = getattr(packet, 'rx_time', None)
            if hasattr(packet, 'hop_start'):
                hop_start = getattr(packet, 'hop_start', None)
            if hasattr(packet, 'hop_limit'):
                hop_limit = getattr(packet, 'hop_limit', None)
        except Exception as e:
            logging.warning(f"Could not extract extra packet fields: {e}")
        # Only set success=False if want_ack is True, otherwise leave as None
        want_ack = getattr(packet, 'want_ack', None)
        DB.add_node_packet(
            from_node_id=from_node_id_str,
            gateway_node_id=gateway_node_dbid if gateway_node_dbid is not None else 0,
            to_node_id=to_node_id_str,
            packet_type=portnum,
            rssi=getattr(packet, 'rssi', None),
            snr=getattr(packet, 'snr', None),
            payload_size=len(decoded_data.payload) if hasattr(decoded_data, 'payload') and decoded_data.payload else None,
            success=False if want_ack else None,
            response_time=None,
            timestamp=datetime.now(),
            channel_id=channel_id,  # Use the string channel id
            packet_id=packet_id,
            rx_rssi=rx_rssi,
            rx_snr=rx_snr,
            rx_time=rx_time,
            hop_start=hop_start,
            hop_limit=hop_limit,
        )
    except Exception as e:
        logging.error(f"Error guardando NodePacket: {e}")

    if callback is not None:
        try:
            # Fix type annotation for callback to avoid mypy/pyright error
            callback = callback  # type: ignore
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
        topic = msg.topic
        envelope = mqtt_pb2.ServiceEnvelope()
        envelope.ParseFromString(msg.payload)
        gateway_node_id = getattr(envelope, 'gateway_id', None)
        channel_id_str = getattr(envelope, 'channel_id', None)  # This is the human-readable channel name/id
        # --- Ensure channel exists in DB and add sender as member ---
        if envelope.HasField('packet'):
            channel_num = getattr(envelope.packet, 'channel', None)
            sender_node_number = getattr(envelope.packet, 'from', None)
            sender_node_id = None
            if sender_node_number is not None:
                node_obj = DB.get_node(sender_node_number)
                if node_obj:
                    sender_node_id_str = node_obj.node_id
                    sender_node_id = node_obj.node_id
                else:
                    sender_node_id = num_to_id(sender_node_number)
            if channel_num is not None:
                if sender_node_id is not None:
                    member_node_ids = [sender_node_id]
                DB.add_or_update_channel(channel_num=channel_num, channel_id=channel_id_str, member_node_ids=member_node_ids)
        else:
            channel_id = getattr(envelope, 'channel_id', None)
            if channel_id is not None:
                fallback_channel_num = abs(hash(channel_id)) % (10 ** 8)
                DB.add_or_update_channel(channel_num=fallback_channel_num, channel_id=channel_id)
        logging.debug(f"Received envelope in topic={topic}\n{envelope}")
        if envelope.HasField('packet'):
            packet = envelope.packet
            try:
                if packet.HasField('decoded'):
                    handle_packet(packet, packet.decoded, enabled_portnums, callback=callback, gateway_node_id=gateway_node_id, channel_id_str=channel_id_str)
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
                                handle_packet(packet, payload, enabled_portnums, callback=callback, gateway_node_id=gateway_node_id, channel_id_str=channel_id_str)
                            else:
                                logging.info(f"[Encrypted] Could not decrypt packet from {from_} ({from_id}, {from_shortname}, {from_longname}) to {packet.to} ({to_id}, {to_shortname}, {to_longname})")
                                # Save encrypted but undecoded packet to DB
                                try:
                                    from_node_id_str = num_to_id(getattr(packet, 'from', 0))
                                    to_node_id_str = num_to_id(getattr(packet, 'to', 0))
                                    packet_id = getattr(packet, 'id', None)
                                    rx_rssi = getattr(packet, 'rx_rssi', None)
                                    rx_snr = getattr(packet, 'rx_snr', None)
                                    rx_time = getattr(packet, 'rx_time', None)
                                    hop_start = getattr(packet, 'hop_start', None)
                                    hop_limit = getattr(packet, 'hop_limit', None)
                                    want_ack = getattr(packet, 'want_ack', None)
                                    # Add or update both from_node and to_node before saving activity
                                    DB.add_or_update_node(
                                        node_number=getattr(packet, 'from', 0),
                                        last_seen=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    )
                                    DB.add_or_update_node(
                                        node_number=getattr(packet, 'to', 0)
                                    )
                                    DB.add_node_packet(
                                        from_node_id=from_node_id_str,
                                        gateway_node_id=gateway_node_id or 0,
                                        to_node_id=to_node_id_str,
                                        packet_type="ENCRYPTED",
                                        rssi=getattr(packet, 'rssi', None),
                                        snr=getattr(packet, 'snr', None),
                                        payload_size=len(packet.encrypted) if hasattr(packet, 'encrypted') and packet.encrypted else None,
                                        success=False if want_ack else None,
                                        response_time=None,
                                        timestamp=datetime.now(),
                                        channel_id=channel_id_str,
                                        packet_id=packet_id,
                                        rx_rssi=rx_rssi,
                                        rx_snr=rx_snr,
                                        rx_time=rx_time,
                                        hop_start=hop_start,
                                        hop_limit=hop_limit,
                                    )
                                    logging.warning(f"[DB] Saved encrypted/undecoded packet from {from_node_id_str} to {to_node_id_str} (id={packet_id}) to DB.")
                                except Exception as e2:
                                    logging.error(f"[DB] Failed to save encrypted/undecoded packet: {e2}")
                        else:
                            logging.info(f"[Encrypted] No key provided for decryption.")
                    else:
                        logging.info(f"[PKI] Trying to decrypt PKI encrypted packet from {from_} ({from_id}, {from_shortname}, {from_longname}) to {packet.to} ({to_id}, {to_shortname}, {to_longname}) (Not implemented yet)")
                        try:
                            from_node_id_str = num_to_id(from_)
                            to_node_id_str = num_to_id(packet.to)
                            packet_id = getattr(packet, 'id', None)
                            rx_rssi = getattr(packet, 'rx_rssi', None)
                            rx_snr = getattr(packet, 'rx_snr', None)
                            rx_time = getattr(packet, 'rx_time', None)
                            hop_start = getattr(packet, 'hop_start', None)
                            hop_limit = getattr(packet, 'hop_limit', None)
                            want_ack = getattr(packet, 'want_ack', None)
                            DB.add_node_packet(
                                from_node_id=from_node_id_str,
                                gateway_node_id=gateway_node_id or 0,
                                to_node_id=to_node_id_str,
                                packet_type="PKI_ENCRYPTED",
                                rssi=getattr(packet, 'rssi', None),
                                snr=getattr(packet, 'snr', None),
                                payload_size=len(packet.encrypted) if hasattr(packet, 'encrypted') and packet.encrypted else None,
                                success=False if want_ack else None,
                                response_time=None,
                                timestamp=datetime.now(),
                                channel_id=channel_id_str,
                                packet_id=packet_id,
                                rx_rssi=rx_rssi,
                                rx_snr=rx_snr,
                                rx_time=rx_time,
                                hop_start=hop_start,
                                hop_limit=hop_limit,
                            )
                            logging.debug(f"[PKI] Saved PKI-encrypted packet from {from_node_id_str} to {to_node_id_str} (id={packet_id}) to DB.")
                        except Exception as e:
                            logging.error(f"[PKI] Failed to save PKI-encrypted packet: {e}")
            except Exception as e:
                # Save undecoded packet with minimal info
                try:
                    from_node_id_str = num_to_id(getattr(packet, 'from', 0))
                    to_node_id_str = num_to_id(getattr(packet, 'to', 0))
                    packet_id = getattr(packet, 'id', None)
                    rx_rssi = getattr(packet, 'rx_rssi', None)
                    rx_snr = getattr(packet, 'rx_snr', None)
                    rx_time = getattr(packet, 'rx_time', None)
                    hop_start = getattr(packet, 'hop_start', None)
                    hop_limit = getattr(packet, 'hop_limit', None)
                    DB.add_node_packet(
                        from_node_id=from_node_id_str,
                        gateway_node_id=gateway_node_id or 0,
                        to_node_id=to_node_id_str,
                        packet_type="UNDECODED",
                        rssi=getattr(packet, 'rssi', None),
                        snr=getattr(packet, 'snr', None),
                        payload_size=len(packet.encrypted) if hasattr(packet, 'encrypted') and packet.encrypted else None,
                        success=False if want_ack else None,
                        response_time=None,
                        timestamp=datetime.now(),
                        channel_id=channel_id_str,
                        packet_id=packet_id,
                        rx_rssi=rx_rssi,
                        rx_snr=rx_snr,
                        rx_time=rx_time,
                        hop_start=hop_start,
                        hop_limit=hop_limit,
                        want_ack=want_ack
                    )
                    logging.warning(f"[DB] Saved undecoded packet from {from_node_id_str} to {to_node_id_str} (id={packet_id}) to DB.")
                except Exception as e2:
                    logging.error(f"[DB] Failed to save undecoded packet: {e2}")
                logging.error(f"[on_message] Failed to decode or process packet: {e}")
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
