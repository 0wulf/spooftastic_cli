# Spooftastic CLI

PoC Meshtastic Spoofing CLI tools for spoofing via MQTT broker.

> Inspired by the great work of [pdxlocation's connect](https://github.com/pdxlocations/connect)

> ![IMPORTANT]
> Always use this tool responsibly and only on networks where you have permission and nodes that you control.

## Overview

Spooftastic CLI is a command-line utility for interacting with Meshtastic networks via MQTT. It allows you to listen to network traffic, send various types of packets (position, nodeinfo, messages), manage a local node database, and perform spoofing of nodeinfo, position and other packet types data for research purposes.

## Features

- **Sniff** Meshtastic MQTT broker traffic and filter by message type.
- **Send** position, nodeinfo, or text messages.
- **Database** management for nodes (list, get, set, delete).
- **Spoof**: Impersonate a node by sending spoofed node activity (position, nodeinfo) in several modes (reactive, periodic, hybrid).

## Requirements

- Meshtastic Python libraries (see [requirements.txt](requirements.txt))
- MQTT broker credentials (see [settings.py](settings.py) and [.env.example](.env.example))

## Installation

1. Clone the repository and enter the directory:
   ```bash
   git clone <repo-url>
   cd spooftastic
   ```

2. Install dependencies (preferably in a virtual environment):
   ```bash
   python -m venv .venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Configure your MQTT and Meshtastic settings in your .env file.

## Usage

Run the CLI tool:
```bash
python spooftastic.py <mode> [options]
```

### Typical Usage Workflow

1. **Populate the database**: Use the sniffer to capture nodeinfo and position packets from the target node. This is necessary to gather the real information of the node you want to spoof.
   ```bash
   python spooftastic.py sniffer --nodeinfo --position
   ```
   Let the sniffer run until it captures the relevant packets. The information will be stored in the local database.

2. **Verify the database**: Check that the node information has been correctly stored.
   ```bash
   python spooftastic.py db nodes list
   # or
   python spooftastic.py db nodes get <node_id>
   ```

3. **Spoofing**: You can now spoof the node. When spoofing, the tool will use the information you provide via command-line arguments. If a parameter is not provided, it will use the value from the database for that node. If the information is not available, it will fall back to a default value.
   ```bash
   python spooftastic.py spoofer --node-id <mac> --short-name "Evil" --lat 12.34 --lon 56.78 periodic --interval 30
   ```
   - Any parameter not provided will be filled from the database entry for that node.
   - If the database entry is missing, a default value is used.

4. **Database freeze**: To prevent spoofed data from altering the original node information, the database entry for a node can be frozen. When the `freeze` column is set to `true`, that entry cannot be modified. This ensures that spoofing does not overwrite the original node data, and spoofed packets are not stored in the database.

### Meshtastic Bots and Bulletin Board Spoofing

Some Meshtastic bots don't check for secure channel when receiving a message, this means that one can issue commands as another user. This bots may include Bulletin Board Services (BBS), which allow nodes to publish messages to a shared board. With spooftastic, you can spoof a node and publish a message to the BBS as if you were that node.

**Example:**
```bash
python spooftastic.py send --to-node <bbs_node_mac> --from-node <spoofed_node_mac> message --message "<pub_bbs_command> <message>"
```
- Replace `<bbs_node_mac>` with the MAC address of the node running the BBS service.
- Replace `<spoofed_node_mac>` with the MAC address of the node you want to impersonate.
- Replace `<pub_bbs_command>` with the actual publish to BBS command for your bot.
- Replace `<message>` with the actual message to publish as the spoofed node.

This will publish a message to the BBS as if it came from the spoofed node. Use this feature responsibly and only on networks where you have permission.

## Modes

### 1. Sniffer

Sniff / listen for incoming packets on the MQTT broker.
```bash
python spooftastic.py sniffer [--text] [--seq] [--position] [--nodeinfo] [--route] [--telemetry]
```
- `--text`: Print incoming text messages
- `--seq`: Print incoming sequence numbers
- `--position`: Print incoming position data
- `--nodeinfo`: Print incoming nodeinfo data
- `--route`: Print incoming routing data
- `--telemetry`: Print incoming telemetry data

### 2. Send

Send data to the network.
```bash
python spooftastic.py send <type> [options]
```
Types:
- `position`: Send position data
- `nodeinfo`: Send nodeinfo data
- `message`: Send a text message

Common options:
- `--gateway-node <mac>`: Gateway node MAC (default: broadcast)
- `--to-node <mac>`: Destination node MAC (default: broadcast)
- `--from-node <mac>`: Source node MAC

**Examples:**

Send a position packet:
```bash
python spooftastic.py send position --lat 12.34 --lon 56.78 --alt 100 --to-node <mac> --from-node <mac>
```
Send a nodeinfo packet:
```bash
python spooftastic.py send nodeinfo --short-name "Test" --long-name "Test Node" --hw-model 43 --to-node <mac> --from-node <mac>
# hw-model 43 corresponds to the HELTEC_V3
```
Send a text message packet:
```bash
python spooftastic.py send message --message "Hello world" --to-node <mac> --from-node <mac>
```

### 3. Database

Manage the local node database.
```bash
python spooftastic.py db nodes list
python spooftastic.py db nodes get <node_id>
python spooftastic.py db nodes set <node_id> <column> <value>
python spooftastic.py db show-nodes
python spooftastic.py db delete
```
- `list`: List all nodes
- `get <node_id>`: Get node by MAC or number
- `set <node_id> <column> <value>`: Set a column value for a node
- `show-nodes`: Show all nodes
- `delete`: Delete the database

### 4. Spoofer

Spoof node data on the network.
```bash
python spooftastic.py spoofer --node-id <id> [options] <spoof_mode> [spoof_mode options]
```
Options:
- `--gateway-node <mac>`: Gateway node MAC (default: broadcast)
- `--to-node <mac>`: Destination node MAC (default: broadcast)
- `--short-name <name>`: Short name of the spoofed node
- `--long-name <name>`: Long name of the spoofed node
- `--hw-model <int>`: Hardware model (e.g., 43 for Heltec V3. Full list at it's official [protobuf definition](https://github.com/meshtastic/python/blob/213faa0cae0504ca5b49a03fa9a3c47c75ecca09/meshtastic/protobuf/mesh_pb2.pyi#L33))
- `--lat <float>`: Latitude
- `--lon <float>`: Longitude
- `--alt <float>`: Altitude
- `--burst <int>`: Number of packets per event (reactive mode)
- `--period <float>`: Seconds between packets in a burst (reactive mode)
- `--restore-after`: Restore original node info after spoofing

Spoofing modes:
- `reactive`: Spoof when receiving nodeinfo/position from the original node
- `periodic`: Spoof periodically (`--interval <seconds>`)
- `hybrid`: Both periodic and reactive (`--interval <seconds>`)

**Examples:**

Spoof `!deadbeef`'s short name, latitude, longitude every 30 seconds:
```bash
python spooftastic.py spoofer --node-id '!deadbeef' --short-name "Evil" --lat 12.34 --lon 56.78 periodic --interval 30
```

Replay with burst of 3 every 2 seconds
```bash
python spooftastic spoofer --node-id '!deadbeef' --burst 3 --period 2 <spoofmode>
```

## Configuration

Copy the `.env.example` file into `.env` and then edit `.env` to set your MQTT broker, credentials, and Meshtastic channel/key.

## Logging

Use `--debug` after calling the main script to enable verbose logging for troubleshooting.
```bash
python spooftastic.py --debug <mode>
```
## Security and Spoofing Considerations

- Spoofing attacks are noisy: spoofed node data is visible to the entire mesh network, unless you are sending a direct message.
- If the victim controls more than one node, they will likely notice spoofing (e.g., their node name changes unexpectedly).
- Spoofing only works if the spoofed packets can reach the victim. If the spoofed packet must traverse the victim node to reach itself, it will be dropped (Meshtastic nodes drop packets sent from themselves).
- Always use this tool responsibly and only on networks where you have permission.

## Future Features

- **Full parameter spoofing**: Spoof all parameters from the database for a node.
- **ATAK spoofing**: Spoof all packets and information from the Meshtastic ATAK module.
- **PKC/PKI decryption**: Ability to decrypt messages using public key cryptography.
- **Virtual Nodes**: Create your own virtual nodes for use in more sophisticated attacks.
- **Spoof-based MitM attack**: Theoretical attack where two controlled nodes impersonate two victims (A and B), relaying and modifying messages between them.


## Contributing

Pull requests and issues are welcome!

## License

GNU General Public License v3.0

---

**Note:** This tool is for research, testing, and educational purposes only. Do not use it to disrupt or impersonate real nodes without permission.
