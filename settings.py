import os
from dotenv import load_dotenv

load_dotenv()

def get_env_or_default(key, default):
    return os.environ.get(key, default)

BROADCAST_MAC = '!ffffffff'
BROADCAST_NUM = int('ffffffff', 16)

# Settings for the application, loaded from environment variables or defaults
MQTT_BROKER = get_env_or_default('MQTT_BROKER', 'mqtt.meshtastic.cl')
MQTT_PORT = int(get_env_or_default('MQTT_PORT', 1883))
MQTT_USERNAME = get_env_or_default('MQTT_USERNAME', 'mshcl2025')
MQTT_PASSWORD = get_env_or_default('MQTT_PASSWORD', 'meshtastic.cl')
ROOT_TOPIC = get_env_or_default('ROOT_TOPIC', 'msh/CL/2/e/')
CHANNEL = get_env_or_default('CHANNEL', 'LongFast')
KEY = get_env_or_default('KEY', 'AQ==')
DEBUG = get_env_or_default('DEBUG', 'False').lower() in ('true', '1', 'yes')
