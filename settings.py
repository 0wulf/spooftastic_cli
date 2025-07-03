import os
from dotenv import load_dotenv
import logging

load_dotenv()

def get_env_or_default(key, default):
    return os.environ.get(key, default)

BROADCAST_MAC = '!ffffffff'
BROADCAST_NUM = int('ffffffff', 16)

# Settings for the application, loaded from environment variables or defaults
MQTT_BROKER = get_env_or_default('MQTT_BROKER', 'mqtt.meshtastic.org')
MQTT_PORT = int(get_env_or_default('MQTT_PORT', 1883))
MQTT_USERNAME = get_env_or_default('MQTT_USERNAME', 'meshdev')
MQTT_PASSWORD = get_env_or_default('MQTT_PASSWORD', 'large4cats')
ROOT_TOPIC = get_env_or_default('ROOT_TOPIC', 'msh/US/2/e/')
CLIENT_ID = get_env_or_default('CLIENT_ID', 'sftcli')
CHANNEL = get_env_or_default('CHANNEL', 'LongFast')
KEY = get_env_or_default('KEY', 'AQ==')
DEBUG = get_env_or_default('DEBUG', 'False').lower() in ('true', '1', 'yes')

# Logging configuration
LOGLEVEL = get_env_or_default('LOGLEVEL', 'INFO').upper()
LOGFORMAT = get_env_or_default('LOGFORMAT', '%(asctime)s - %(levelname)s - %(message)s')
LOGDATEFMT = get_env_or_default('LOGDATEFMT', '%Y-%m-%d %H:%M:%S')

logging.basicConfig(
    level=LOGLEVEL,
    format=LOGFORMAT,
    datefmt=LOGDATEFMT
)
