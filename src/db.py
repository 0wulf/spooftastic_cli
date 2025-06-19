from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, ValidationError
from typing import Optional
import threading
import os

from src.utils import num_to_id, num_to_mac

# SQLite database file
DB_URL = 'sqlite:///meshtastic_nodes.db'
Base = declarative_base()

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
    pubkey = Column(String, nullable=True)  # <-- Add this line
    temperature = Column(Float, nullable=True)
    relative_humidity = Column(Float, nullable=True)
    barometric_pressure = Column(Float, nullable=True)
    voltage = Column(Float, nullable=True)
    battery_level = Column(Float, nullable=True)
    rssi = Column(Float, nullable=True)
    snr = Column(Float, nullable=True)
    last_seen = Column(String, nullable=True)
    freeze = Column(Boolean, default=False, nullable=False)  # New freeze column

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
    temperature: Optional[float] = None
    relative_humidity: Optional[float] = None
    barometric_pressure: Optional[float] = None
    voltage: Optional[float] = None
    battery_level: Optional[float] = None
    rssi: Optional[float] = None
    snr: Optional[float] = None
    last_seen: Optional[str] = None  
    freeze: bool = False  # New freeze field

    class Config:
        from_attributes = True

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

    def get_session(self) -> Session:
        return self._SessionLocal()

    def add_or_update_node(self, node_number, short_name=None, long_name=None, lat=None, lon=None, alt=None, hw_model=None, pubkey=None, temperature=None, relative_humidity=None, barometric_pressure=None, voltage=None, battery_level=None, rssi=None, snr=None, last_seen=None, freeze=None):
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
                        temperature=temperature,
                        relative_humidity=relative_humidity,
                        barometric_pressure=barometric_pressure,
                        voltage=voltage,
                        battery_level=battery_level,
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
                return [NodeModel.model_validate(node) for node in nodes]
            finally:
                db.close()

    def delete_database(self):
        """Delete the SQLite database file and reinitialize the engine."""
        with self._db_lock:
            self._engine.dispose()
            db_path = DB_URL.replace('sqlite:///', '')
            if os.path.exists(db_path):
                os.remove(db_path)
            # Reinitialize DB after deletion
            self._init_db()

    def set_freeze(self, node_id, freeze: bool):
        """
        Set the freeze state of a node by node_mac or node_number.
        """
        with self._db_lock:
            db = self.get_session()
            try:
                node = None
                # Try by node_mac first
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

# Singleton instance
DB = DBClient()
