from sqlalchemy import Column, Integer, String, Float, Boolean, Table, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Optional
import enum

Base = declarative_base()

channel_node_association = Table(
    'channel_node_association', Base.metadata,
    Column('channel_num', Integer, ForeignKey('channels.channel_num'), primary_key=True),
    Column('node_id', Integer, ForeignKey('nodes.id'), primary_key=True)
)

class Node(Base):
    __tablename__ = 'nodes'
    id = Column(Integer, primary_key=True, index=True)
    node_number = Column(Integer, unique=True, nullable=False)
    node_mac = Column(String, unique=True, nullable=False)
    node_id = Column(String, unique=True, nullable=False)
    short_name = Column(String, nullable=True)
    long_name = Column(String, nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    alt = Column(Float, nullable=True)
    hw_model = Column(String, nullable=True)
    pubkey = Column(String, nullable=True)
    battery_level = Column(Integer, nullable=True)
    voltage = Column(Float, nullable=True)
    channel_utilization = Column(Float, nullable=True)
    air_util_tx = Column(Float, nullable=True)
    uptime_seconds = Column(Integer, nullable=True)
    temperature = Column(Float, nullable=True)
    relative_humidity = Column(Float, nullable=True)
    barometric_pressure = Column(Float, nullable=True)
    gas_resistance = Column(Float, nullable=True)
    iaq = Column(Float, nullable=True)
    rssi = Column(Float, nullable=True)
    snr = Column(Float, nullable=True)
    last_seen = Column(String, nullable=True)
    freeze = Column(Boolean, default=False, nullable=False)
    channels = relationship('Channel', secondary=channel_node_association, back_populates='member_nodes')
    packets_from = relationship('NodePacket', foreign_keys='NodePacket.from_node_id', back_populates='from_node')
    packets_gateway = relationship('NodePacket', foreign_keys='NodePacket.gateway_node_id', back_populates='gateway_node')
    packets_to = relationship('NodePacket', foreign_keys='NodePacket.to_node_id', back_populates='peer_node')

class NodeModel(BaseModel):
    id: Optional[int]
    node_number: int
    node_mac: str
    node_id: str
    short_name: Optional[str] = None
    long_name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    alt: Optional[float] = None
    hw_model: Optional[str] = None
    pubkey: Optional[str] = None
    battery_level: Optional[int] = None
    voltage: Optional[float] = None
    channel_utilization: Optional[float] = None
    air_util_tx: Optional[float] = None
    uptime_seconds: Optional[int] = None
    temperature: Optional[float] = None
    relative_humidity: Optional[float] = None
    barometric_pressure: Optional[float] = None
    gas_resistance: Optional[float] = None
    iaq: Optional[float] = None
    rssi: Optional[float] = None
    snr: Optional[float] = None
    last_seen: Optional[str] = None
    freeze: bool = False
    class Config:
        from_attributes = True

class Channel(Base):
    __tablename__ = 'channels'
    channel_num = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String, nullable=False)  # removed unique=True
    aes_key = Column(String, nullable=True)
    member_nodes = relationship('Node', secondary=channel_node_association, back_populates='channels')

class ChannelModel(BaseModel):
    channel_num: int
    channel_id: str
    aes_key: Optional[str] = None
    member_nodes: Optional[list[str]] = None
    class Config:
        from_attributes = True

class NodePacket(Base):
    __tablename__ = 'node_packet'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, index=True, nullable=False)
    from_node_id = Column(Integer, ForeignKey('nodes.id'), nullable=False)
    gateway_node_id = Column(Integer, ForeignKey('nodes.id'), nullable=False)
    to_node_id = Column(Integer, ForeignKey('nodes.id'), nullable=False)
    packet_type = Column(String, nullable=True)
    rssi = Column(Float, nullable=True)
    snr = Column(Float, nullable=True)
    payload_size = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=True)
    response_time = Column(Float, nullable=True)
    channel_id = Column(String, nullable=True)  # NEW: store channel_id from envelope
    packet_id = Column(Integer, nullable=True)  # NEW: store packet.id from protobuf
    rx_rssi = Column(Float, nullable=True)  # NEW: store rx_rssi from packet
    rx_snr = Column(Float, nullable=True)   # NEW: store rx_snr from packet
    rx_time = Column(Integer, nullable=True)  # CHANGED: store rx_time as Integer
    hop_start = Column(Integer, nullable=True)  # NEW: store hop_start from packet
    hop_limit = Column(Integer, nullable=True)  # NEW: store hop_limit from packet

    from_node = relationship('Node', foreign_keys=[from_node_id], back_populates='packets_from')
    gateway_node = relationship('Node', foreign_keys=[gateway_node_id], back_populates='packets_gateway')
    peer_node = relationship('Node', foreign_keys=[to_node_id], back_populates='packets_to')

class NodePacketModel(BaseModel):
    id: Optional[int]
    timestamp: str
    from_node_id: int
    gateway_node_id: int
    to_node_id: int
    packet_type: Optional[str] = None
    rssi: Optional[float] = None
    snr: Optional[float] = None
    payload_size: Optional[int] = None
    success: Optional[bool] = None
    response_time: Optional[float] = None
    channel_id: Optional[str] = None  # NEW
    packet_id: Optional[int] = None   # NEW
    rx_rssi: Optional[float] = None  # NEW
    rx_snr: Optional[float] = None   # NEW
    rx_time: Optional[int] = None  # CHANGED: rx_time is now Optional[int]
    hop_start: Optional[int] = None  # NEW
    hop_limit: Optional[int] = None  # NEW
    class Config:
        from_attributes = True
