from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import threading
import os
from src.utils import num_to_id, num_to_mac
from settings import CHANNEL, KEY
from src.models import Node, Channel, channel_node_association, Base, NodeModel, ChannelModel
from pydantic import ValidationError
import logging

DB_URL = 'sqlite:///meshtastic_nodes.db'

class DBClient:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        self._engine = create_engine(DB_URL, echo=False, connect_args={"check_same_thread": False})
        self._SessionLocal = sessionmaker(bind=self._engine)
        Base.metadata.create_all(bind=self._engine)
        self._db_lock = threading.RLock()
        # Ensure default channel exists
        with self._db_lock:
            db = self.get_session()
            try:
                channel_num = abs(hash(CHANNEL)) % (10 ** 8)
                channel = db.query(Channel).filter_by(channel_id=CHANNEL).first()
                if not channel:
                    channel = Channel(channel_num=channel_num, channel_id=CHANNEL, aes_key=KEY)
                    db.add(channel)
                    db.commit()
            finally:
                db.close()

    def get_session(self) -> Session:
        return self._SessionLocal()

    def add_or_update_node(
            self,
            node_number,
            short_name=None,
            long_name=None,
            lat=None,
            lon=None,
            alt=None,
            hw_model=None,
            pubkey=None,
            battery_level=None,
            voltage=None,
            channel_utilization=None,
            air_util_tx=None,
            uptime_seconds=None,
            temperature=None,
            relative_humidity=None,
            barometric_pressure=None,
            gas_resistance=None,
            iaq=None,
            rssi=None,
            snr=None,
            last_seen=None,
            freeze=None,
    ):
        node_mac = num_to_mac(node_number)
        node_id = num_to_id(node_number)
        with self._db_lock:
            db = self.get_session()
            try:
                node = db.query(Node).filter((Node.node_number == node_number) | (Node.node_mac == node_mac) | (Node.node_id == node_id)).first()
                if not node:
                    node = Node(
                        node_number=node_number,
                        node_mac=node_mac,
                        node_id=node_id,
                        short_name=short_name,
                        long_name=long_name,
                        lat=lat,
                        lon=lon,
                        alt=alt,
                        hw_model=hw_model,
                        pubkey=pubkey,
                        battery_level=battery_level,
                        voltage=voltage,
                        channel_utilization=channel_utilization,
                        air_util_tx=air_util_tx,
                        uptime_seconds=uptime_seconds,
                        temperature=temperature,
                        relative_humidity=relative_humidity,
                        barometric_pressure=barometric_pressure,
                        gas_resistance=gas_resistance,
                        iaq=iaq,
                        rssi=rssi,
                        snr=snr,
                        last_seen=last_seen,
                        freeze=freeze if freeze is not None else False
                    )
                    db.add(node)
                else:
                    # If freeze is True, only allow updating freeze field
                    if getattr(node, 'freeze', False):
                        if freeze is not None:
                            setattr(node, 'freeze', freeze)
                        db.commit()
                        db.refresh(node)
                        try:
                            node_model = NodeModel.model_validate(node)
                        except ValidationError as e:
                            raise ValueError(f"Node data validation failed: {e}")
                        return node_model
                    # If freeze is being set/unset, allow it
                    if freeze is not None:
                        setattr(node, 'freeze', freeze)
                    if node_mac is not None:
                        node.node_mac = node_mac
                    if node_number is not None:
                        node.node_number = node_number
                    if node_id is not None:
                        node.node_id = node_id
                    if short_name is not None:
                        node.short_name = short_name
                    if long_name is not None:
                        node.long_name = long_name
                    if lat is not None:
                        node.lat = lat
                    if lon is not None:
                        node.lon = lon
                    if alt is not None:
                        node.alt = alt
                    if hw_model is not None:
                        node.hw_model = hw_model
                    if pubkey is not None:
                        node.pubkey = pubkey
                    if temperature is not None:
                        node.temperature = temperature
                    if relative_humidity is not None:
                        node.relative_humidity = relative_humidity
                    if barometric_pressure is not None:
                        node.barometric_pressure = barometric_pressure
                    if voltage is not None:
                        node.voltage = voltage
                    if battery_level is not None:
                        node.battery_level = battery_level
                    if channel_utilization is not None:
                        node.channel_utilization = channel_utilization
                    if air_util_tx is not None:
                        node.air_util_tx = air_util_tx
                    if uptime_seconds is not None:
                        node.uptime_seconds = uptime_seconds
                    if gas_resistance is not None:
                        node.gas_resistance = gas_resistance
                    if iaq is not None:
                        node.iaq = iaq
                    if rssi is not None:
                        node.rssi = rssi
                    if snr is not None:
                        node.snr = snr
                    if last_seen is not None:
                        node.last_seen = last_seen
                db.commit()
                db.refresh(node)
                try:
                    node_model = NodeModel.model_validate(node)
                except ValidationError as e:
                    raise ValueError(f"Node data validation failed: {e}")
                return node_model
            finally:
                db.close()

    def get_node(self, node_number):
        with self._db_lock:
            db = self.get_session()
            try:
                node = db.query(Node).filter_by(node_number=node_number).first()
                if node:
                    try:
                        return NodeModel.model_validate(node)
                    except ValidationError as e:
                        raise ValueError(f"Node data validation failed: {e}")
                return None
            finally:
                db.close()

    def get_all_nodes(self):
        with self._db_lock:
            db = self.get_session()
            try:
                nodes = db.query(Node).all()
                node_list = [NodeModel.model_validate(node) for node in nodes]
                # Fix: sort with None last_seen as empty string, so all are comparable
                def safe_last_seen(x):
                    return x.last_seen if x.last_seen is not None else ''
                node_list.sort(key=safe_last_seen, reverse=True)
                return node_list
            finally:
                db.close()

    def delete_database(self):
        """Delete the SQLite database file and reinitialize the engine."""
        with self._db_lock:
            self._engine.dispose()
            db_path = DB_URL.replace('sqlite:///', '')
            if os.path.exists(db_path):
                os.remove(db_path)
            self._init_db()

    def set_freeze(self, node_id, freeze: bool):
        """
        Set the freeze state of a node by node_mac or node_number.
        """
        with self._db_lock:
            db = self.get_session()
            try:
                node = None
                if isinstance(node_id, str):
                    node = db.query(Node).filter_by(node_mac=node_id).first()
                if not node:
                    try:
                        node_number = int(node_id)
                        node = db.query(Node).filter_by(node_number=node_number).first()
                    except Exception:
                        pass
                if node:
                    setattr(node, 'freeze', freeze)
                    db.commit()
                    db.refresh(node)
                    try:
                        return NodeModel.model_validate(node)
                    except ValidationError as e:
                        raise ValueError(f"Node data validation failed: {e}")
                return None
            finally:
                db.close()

    def resolve_node_names(self, node_number):
        """
        Resolve short and long names for a node by its node_number.
        Returns a tuple of (short_name, long_name).
        """

        with self._db_lock:
            db = self.get_session()
            try:
                node = db.query(Node).filter_by(node_number=node_number).first()
                if node:
                    return node.short_name, node.long_name
                return None, None
            finally:
                db.close()

    def add_or_update_channel(self, channel_num, channel_id=None, member_node_ids=None, aes_key=None):
        """
        Add or update a channel by channel_num (primary key). Channels may share the same channel_id (name).
        If member_node_ids is provided, add those nodes to the channel's members (do not remove existing ones).
        """
        with self._db_lock:
            db = self.get_session()
            try:
                channel = db.query(Channel).filter(Channel.channel_num == channel_num).first()
                if not channel:
                    channel = Channel(channel_num=channel_num, channel_id=channel_id)
                    db.add(channel)
                else:
                    if channel_id is not None:
                        channel.channel_id = channel_id
                if aes_key is not None:
                    channel.aes_key = aes_key
                if member_node_ids is not None:
                    # Only add new members, do not remove existing ones
                    existing_members = set(n.node_id for n in channel.member_nodes) if channel.member_nodes else set()
                    new_members = set(member_node_ids)
                    all_members = existing_members.union(new_members)
                    nodes = db.query(Node).filter(Node.node_id.in_(all_members)).all()
                    channel.member_nodes = nodes
                db.commit()
                db.refresh(channel)
                member_node_ids_out = [n.node_id for n in channel.member_nodes] if channel.member_nodes else []
                return ChannelModel(channel_num=channel.channel_num, channel_id=channel.channel_id, aes_key=channel.aes_key, member_nodes=member_node_ids_out)
            finally:
                db.close()

    def get_channel(self, channel_num):
        with self._db_lock:
            db = self.get_session()
            try:
                channel = db.query(Channel).filter_by(channel_num=channel_num).first()
                if channel:
                    member_node_ids = [n.node_id for n in channel.member_nodes] if channel.member_nodes else []
                    return ChannelModel(channel_num=channel.channel_num, channel_id=channel.channel_id, aes_key=channel.aes_key, member_nodes=member_node_ids)
                return None
            finally:
                db.close()

    def get_all_channels(self):
        with self._db_lock:
            db = self.get_session()
            try:
                channels = db.query(Channel).all()
                return [ChannelModel(channel_num=c.channel_num, channel_id=c.channel_id, aes_key=c.aes_key, member_nodes=[n.node_id for n in c.member_nodes] if c.member_nodes else []) for c in channels]
            finally:
                db.close()

    def add_node_packet(self, from_node_id, gateway_node_id, to_node_id, packet_type=None, rssi=None, snr=None, payload_size=None, success=None, response_time=None, timestamp=None, channel_id=None, packet_id=None, rx_rssi=None, rx_snr=None, rx_time=None, hop_start=None, hop_limit=None, want_ack=None):
        """
        Guarda un nuevo paquete de nodo en la base de datos.
        Only sets success=False if want_ack is True. Otherwise, success is None.
        """
        from src.models import NodePacket
        from datetime import datetime
        with self._db_lock:
            db = self.get_session()
            try:
                # Only set success=False if want_ack is True
                if want_ack is not None:
                    if want_ack:
                        success_val = False if success is None else success
                    else:
                        success_val = None
                else:
                    success_val = success
                packet = NodePacket(
                    from_node_id=from_node_id,
                    gateway_node_id=gateway_node_id,
                    to_node_id=to_node_id,
                    packet_type=packet_type,
                    rssi=rssi,
                    snr=snr,
                    payload_size=payload_size,
                    success=success_val,
                    response_time=response_time,
                    timestamp=timestamp or datetime.now(),
                    channel_id=channel_id,
                    packet_id=packet_id,
                    rx_rssi=rx_rssi,
                    rx_snr=rx_snr,
                    rx_time=rx_time,
                    hop_start=hop_start,
                    hop_limit=hop_limit
                )
                db.add(packet)
                db.commit()
                db.refresh(packet)
                return packet
            finally:
                db.close()

    def get_node_packet(self, node_id: str, limit: int = 100):
        """
        Devuelve los paquetes del nodo dado (por node_id tipo !abcd1234), ordenados por timestamp descendente.
        Incluye paquetes donde el nodo es emisor o receptor.
        """
        from src.models import Node, NodePacket
        from sqlalchemy import or_
        with self._db_lock:
            db = self.get_session()
            try:
                node = db.query(Node).filter(Node.node_id == node_id).first()
                if not node:
                    return []
                packets = db.query(NodePacket).filter(
                    or_(NodePacket.from_node_id == node.id, NodePacket.to_node_id == node.id)
                ).order_by(NodePacket.timestamp.desc()).limit(limit).all()
                return packets
            finally:
                db.close()

    def mark_packet_success_by_ack(self, request_id):
        """
        Mark the NodePacket with packet_id=request_id as success=True, regardless of node_id.
        Returns True if a packet was updated, False otherwise.
        """
        from src.models import NodePacket
        with self._db_lock:
            db = self.get_session()
            try:
                query = db.query(NodePacket).filter(NodePacket.packet_id == request_id)
                candidates = query.order_by(NodePacket.timestamp.desc()).all()
                logging.debug(f"[ACK-DEBUG] Candidates for packet_id={request_id}: {[p.id for p in candidates]}")
                packet = candidates[0] if candidates else None
                if packet:
                    packet.success = True
                    db.commit()
                    return True
                return False
            finally:
                db.close()

    @staticmethod
    def update_channel_membership_callback(packet, decoded_data, portnum, from_node_id, to_node_id, **kwargs):
        """
        Callback to update channel membership in the DB when a packet is received.
        """
        from settings import CHANNEL
        try:
            channel_num = getattr(packet, 'channel', None)
            if channel_num is None:
                return
            channel_id = getattr(packet, 'channel_id', None) or CHANNEL or str(channel_num)
            db = DBClient()
            channel = db.get_channel(channel_num)
            member_node_ids = set(channel.member_nodes) if channel and channel.member_nodes else set()
            if from_node_id:
                member_node_ids.add(from_node_id)
            db.add_or_update_channel(
                channel_num=channel_num,
                channel_id=channel_id,
                member_node_ids=list(member_node_ids)
            )
        except Exception as e:
            logging.error(f"[ChannelMembership] Failed to update channel membership: {e}")

# Singleton instance
DB = DBClient()

update_channel_membership_callback = DBClient.update_channel_membership_callback
