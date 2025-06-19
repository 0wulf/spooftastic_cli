from meshtastic.protobuf import mesh_pb2, mqtt_pb2, portnums_pb2
import time
import base64
import re
from src.utils import generate_hash
from src.mesh.encryption import encrypt_message

def generate_mesh_packet(destination_id, encoded_message, node_number, channel, key, global_message_id, node_name, publish_topic, mqtt_client, debug=False):
    mesh_packet = mesh_pb2.MeshPacket()
    mesh_packet.id = global_message_id
    setattr(mesh_packet, "from", node_number)
    mesh_packet.to = destination_id
    mesh_packet.want_ack = False
    mesh_packet.channel = generate_hash(channel, key)
    mesh_packet.hop_limit = 3
    mesh_packet.hop_start = 3
    if key == "":
        mesh_packet.decoded.CopyFrom(encoded_message)
    else:
        mesh_packet.encrypted = encrypt_message(channel, key, mesh_packet, encoded_message, node_number)
    service_envelope = mqtt_pb2.ServiceEnvelope()
    service_envelope.packet.CopyFrom(mesh_packet)
    service_envelope.channel_id = channel
    service_envelope.gateway_id = node_name
    payload = service_envelope.SerializeToString()
    if mqtt_client and mqtt_client.is_connected():
        mqtt_client.publish(publish_topic, payload)
    else:
        if debug: print("MQTT client not connected, cannot publish message.")

def send_message(destination_mac, message_text, node_mac, channel, key, global_message_id, node_name, publish_topic, mqtt_client, debug=False):
    # Ensure destination_mac and node_mac are strings
    if not isinstance(destination_mac, str):
        destination_mac = f"!{destination_mac:x}"
    if not isinstance(node_mac, str):
        node_mac = f"!{node_mac:x}"
    if debug: print(f"Sending Text Message Packet to {str(destination_mac)}")
    destination_id = int(destination_mac[1:], 16)
    node_number = int(node_mac[1:], 16)
    if message_text:
        encoded_message = mesh_pb2.Data()
        encoded_message.portnum = portnums_pb2.TEXT_MESSAGE_APP
        encoded_message.payload = message_text.encode("utf-8")
        encoded_message.bitfield = 1
        generate_mesh_packet(
            destination_id, encoded_message, node_number, channel, key, global_message_id, node_name, publish_topic, mqtt_client, debug
        )
    else:
        return

def send_traceroute(destination_id, node_number, channel, key, global_message_id, node_name, publish_topic, mqtt_client, debug=False):
    if debug: print(f"Sending Traceroute Packet to {str(destination_id)}")
    encoded_message = mesh_pb2.Data()
    encoded_message.portnum = portnums_pb2.TRACEROUTE_APP
    encoded_message.want_response = True
    encoded_message.bitfield = 1
    destination_id = int(destination_id[1:], 16)
    generate_mesh_packet(
        destination_id, encoded_message, node_number, channel, key, global_message_id, node_name, publish_topic, mqtt_client, debug
    )

def send_node_info(destination_mac, want_response, node_mac, channel, key, global_message_id, node_name, client_long_name, client_short_name, client_hw_model, client_pubkey, publish_topic, mqtt_client, debug=False):
    # Ensure destination_mac and node_mac are strings
    if not isinstance(destination_mac, str):
        destination_mac = f"!{destination_mac:x}"
    if not isinstance(node_mac, str):
        node_mac = f"!{node_mac:x}"
    if debug: print(f"Sending NodeInfo Packet to {str(destination_mac)}")
    destination_id = int(destination_mac[1:], 16)
    node_number = int(node_mac[1:], 16)
    user_payload = mesh_pb2.User()
    setattr(user_payload, "id", node_mac[1:])
    setattr(user_payload, "long_name", client_long_name)
    setattr(user_payload, "short_name", client_short_name)
    setattr(user_payload, "hw_model", client_hw_model)
    if client_pubkey:
        # Expect client_pubkey as hex string, decode to bytes for protobuf
        setattr(user_payload, "public_key", bytes.fromhex(client_pubkey))
    user_payload = user_payload.SerializeToString()
    encoded_message = mesh_pb2.Data()
    encoded_message.portnum = portnums_pb2.NODEINFO_APP
    encoded_message.payload = user_payload
    encoded_message.bitfield = 1
    encoded_message.want_response = want_response
    generate_mesh_packet(
        destination_id, encoded_message, node_number, channel, key, global_message_id, node_name, publish_topic, mqtt_client, debug
    )

def send_position(destination_id, lat, lon, alt, node_number, channel, key, global_message_id, node_name, publish_topic, mqtt_client, debug=False):
    # Ensure destination_id and node_number are strings
    if not isinstance(destination_id, str):
        destination_id = f"!{destination_id:x}"
    if not isinstance(node_number, str):
        node_number = f"!{node_number:x}"
    if debug: print(f"Sending Position Packet to {str(destination_id)}")
    pos_time = int(time.time())
    latitude = int(float(lat) * 1e7)
    longitude = int(float(lon) * 1e7)
    altitude_units = 1 / 3.28084 if 'ft' in str(alt) else 1.0
    altitude = int(altitude_units * float(re.sub('[^0-9.]', '', str(alt))))
    position_payload = mesh_pb2.Position()
    setattr(position_payload, "latitude_i", latitude)
    setattr(position_payload, "longitude_i", longitude)
    setattr(position_payload, "altitude", altitude)
    setattr(position_payload, "time", pos_time)
    position_payload = position_payload.SerializeToString()
    encoded_message = mesh_pb2.Data()
    encoded_message.portnum = portnums_pb2.POSITION_APP
    encoded_message.payload = position_payload
    encoded_message.bitfield = 1
    encoded_message.want_response = True
    generate_mesh_packet(
        int(destination_id[1:], 16), encoded_message, int(node_number[1:], 16), channel, key, global_message_id, node_name, publish_topic, mqtt_client, debug
    )

def send_ack(destination_id, message_id, node_number, channel, key, global_message_id, node_name, publish_topic, mqtt_client, debug=False):
    if debug: print("Sending ACK")
    encoded_message = mesh_pb2.Data()
    encoded_message.portnum = portnums_pb2.ROUTING_APP
    encoded_message.request_id = message_id
    encoded_message.payload = b"\030\000"
    generate_mesh_packet(
        destination_id, encoded_message, node_number, channel, key, global_message_id, node_name, publish_topic, mqtt_client, debug
    )
