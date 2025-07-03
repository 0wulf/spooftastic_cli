import base64
import logging
import os

from prettytable import PrettyTable

from meshtastic.protobuf import mesh_pb2

def xor_hash(data):
    result = 0
    for char in data:
        result ^= char
    return result

def ensure_aes_key(key):
    if key == "AQ==" or key is None:
        logging.debug("key is default, expanding to AES128")
        key = "1PG7OiApB1nwvP+rz05pAQ=="
    return key

def set_topic(node_mac, root_topic, channel):
    return root_topic + channel + "/" + node_mac

def generate_hash(name, key):
    replaced_key = key.replace('-', '+').replace('_', '/')
    key_bytes = base64.b64decode(replaced_key.encode('utf-8'))
    h_name = xor_hash(bytes(name, 'utf-8'))
    h_key = xor_hash(key_bytes)
    result = h_name ^ h_key
    return result

def num_to_id(num):
    """Convert a node_number to an node_id address string."""
    num = int(num) if isinstance(num, str) else num
    hex = f"{num:08x}".lower()
    return f"!{hex}"

def id_to_num(node_id):
    """Convert a node_id address string to a node_number."""
    if not isinstance(node_id, str) or not node_id.startswith('!'):
        raise ValueError("Node ID must start with '!'")
    try:
        return int(node_id[1:], 16)
    except ValueError:
        raise ValueError("Invalid node ID format") from None

def num_to_mac(num):
    """Convert a node_number to a MAC address string."""
    num = int(num) if isinstance(num, str) else num
    hex = f"{num:012x}".lower()
    return f"{hex[:2]}:{hex[2:4]}:{hex[4:6]}:{hex[6:8]}:{hex[8:10]}:{hex[10:12]}"

def hw_num_to_model(hw_model_n):
    """Convert a hardware model number to its name."""
    hw_model_int = int(hw_model_n) if isinstance(hw_model_n, str) else hw_model_n
    if hw_model_int is None:
        return None
    return mesh_pb2.HardwareModel.Name(hw_model_int) if hw_model_int else None

def hw_model_to_num(hw_model):
    """Convert a hardware model name to its number."""
    if hw_model is None:
        return None
    return mesh_pb2.HardwareModel.Value(hw_model) if isinstance(hw_model, str) else hw_model


def print_table(data, headers=None):
    """
    Print a table in a formatted way.
    Use the library 'prettytable' for better formatting.
    """
    
    if not data:
        logging.warning("No data to display in table.")
        return

    table = PrettyTable()
    
    if headers:
        table.field_names = headers
    else:
        table.field_names = data[0].keys() if isinstance(data, list) and data else []

    for row in data:
        if isinstance(row, dict):
            row = {k: (v if v is not None else '-') for k, v in row.items()}
            table.add_row(row.values())
        else:
            table.add_row(row)

    print(table)

def clear_screen():
    # Works for most Unix and Windows terminals
    os.system('cls' if os.name == 'nt' else 'clear')