import logging
import ast
import time
from datetime import datetime, timedelta
from src.clients.db_client import DB
from src.utils import hw_num_to_model, print_table
from src.models import NodePacket, Node


def handle_db_mode(args):
    db = DB
    follow = getattr(args, 'follow', False)
    def run_once():
        if getattr(args, 'db_action', None) == 'nodes':
            if args.nodes_action == 'position':
                nodes = db.get_all_nodes()
                nodes_table = []
                for node in nodes:
                    nodes_table.append({
                        'node_number': node.node_number,
                        'node_id': node.node_id,
                        'short_name': node.short_name,
                        'long_name': node.long_name,
                        'lat': node.lat,
                        'lon': node.lon,
                        'alt': node.alt
                    })
                if nodes_table:
                    sort_col = getattr(args, 'sort', None) or 'node_number'
                    sort_col_key = sort_col.lower().replace(' ', '_')
                    if sort_col_key not in nodes_table[0]:
                        sort_col_key = 'node_number'
                    nodes_table.sort(key=lambda x: (x[sort_col_key] if x[sort_col_key] is not None else float('-inf')), reverse=True)
                    print_table(nodes_table, headers=['Node Number', 'Node ID', 'Short Name', 'Long Name', 'Latitude', 'Longitude', 'Altitude'])
            elif args.nodes_action == 'list':
                nodes = db.get_all_nodes()
                nodes_table = []
                for node in nodes:
                    nodes_table.append({
                        'node_number': node.node_number,
                        'node_id': node.node_id,
                        'mac': node.node_mac,
                        'short_name': node.short_name,
                        'long_name': node.long_name,
                        'hw_model': hw_num_to_model(node.hw_model),
                        'pubkey': getattr(node, 'pubkey', None),
                        'freeze': getattr(node, 'freeze', False),
                        'last_seen': getattr(node, 'last_seen', None),
                        'rssi': getattr(node, 'rssi', None),
                        'snr': getattr(node, 'snr', None),
                    })
                if nodes_table:
                    sort_col = getattr(args, 'sort', None) or 'node_number'
                    sort_col_key = sort_col.lower().replace(' ', '_')
                    if sort_col_key not in nodes_table[0]:
                        sort_col_key = 'node_number'
                    # Fix: handle None values for last_seen as the sort key
                    def safe_sort_key(x):
                        v = x.get(sort_col_key)
                        if sort_col_key == 'last_seen':
                            return v if v is not None else ''
                        return v if v is not None else float('-inf')
                    nodes_table.sort(key=safe_sort_key, reverse=True)
                    print_table(nodes_table, headers=['Node Number', 'Node ID', 'Node MAC', 'Short Name', 'Long Name', 'HW Model', 'Pubkey', 'Freeze', 'Last Seen', 'RSSI', 'SNR'])
            elif args.nodes_action == 'environment':
                nodes = db.get_all_nodes()
                env_table = []
                for node in nodes:
                    env_table.append({
                        'node_id': node.node_id,
                        'short_name': node.short_name,
                        'long_name': node.long_name,
                        'temperature': getattr(node, 'temperature', None),
                        'relative_humidity': getattr(node, 'relative_humidity', None),
                        'barometric_pressure': getattr(node, 'barometric_pressure', None),
                        'gas_resistance': getattr(node, 'gas_resistance', None),
                        'iaq': getattr(node, 'iaq', None),
                    })
                if env_table:
                    sort_col = getattr(args, 'sort', None) or 'temperature'
                    sort_col_key = sort_col.lower().replace(' ', '_')
                    if sort_col_key not in env_table[0]:
                        sort_col_key = 'temperature'
                    env_table.sort(key=lambda x: (x[sort_col_key] if x[sort_col_key] is not None else float('-inf')), reverse=True)
                    print_table(env_table, headers=['Node ID', 'Short Name', 'Long Name', 'Temperature', 'Relative Humidity', 'Barometric Pressure', 'Gas Resistance', 'IAQ'])
            elif args.nodes_action == 'device':
                nodes = db.get_all_nodes()
                device_table = []
                for node in nodes:
                    device_table.append({
                        'node_id': node.node_id,
                        'short_name': node.short_name,
                        'long_name': node.long_name,
                        'battery_level': getattr(node, 'battery_level', None),
                        'voltage': getattr(node, 'voltage', None),
                        'channel_utilization': getattr(node, 'channel_utilization', None),
                        'air_util_tx': getattr(node, 'air_util_tx', None),
                        'uptime_seconds': getattr(node, 'uptime_seconds', None),
                    })
                if device_table:
                    sort_col = getattr(args, 'sort', None) or 'battery_level'
                    sort_col_key = sort_col.lower().replace(' ', '_')
                    if sort_col_key not in device_table[0]:
                        sort_col_key = 'battery_level'
                    device_table.sort(key=lambda x: (x[sort_col_key] if x[sort_col_key] is not None else float('-inf')), reverse=True)
                    print_table(device_table, headers=['Node ID', 'Short Name', 'Long Name', 'Battery Level', 'Voltage', 'Channel Utilization', 'Air Util TX', 'Uptime Seconds'])
            elif args.nodes_action == 'get':
                node_id = args.node_id
                node = None
                try:
                    node_number = int(node_id)
                    node = db.get_node(node_number)
                except ValueError:
                    for n in db.get_all_nodes():
                        if n.node_mac == node_id:
                            node = n
                            break
                if node:
                    logging.info(f"Node: {node.node_number}, MAC: {node.node_mac}, Short Name: {node.short_name}, Long Name: {node.long_name}, "
                        f"Lat: {node.lat}, Lon: {node.lon}, Alt: {node.alt}, HW Model: {hw_num_to_model(node.hw_model)}, Pubkey: {getattr(node, 'pubkey', None)}, Freeze: {getattr(node, 'freeze', False)}")
                else:
                    logging.info(f"Node not found: {node_id}")
            elif args.nodes_action == 'set':
                node_id = args.node_id
                column = args.column
                value = args.value
                node = None
                try:
                    node_number = int(node_id)
                    node = db.get_node(node_number)
                except ValueError:
                    for n in db.get_all_nodes():
                        if n.node_mac == node_id:
                            node = n
                            break
                if not node:
                    logging.info(f"Node not found: {node_id}")
                    return
                valid_columns = set(node.__dict__.keys())
                if column not in valid_columns:
                    logging.info(f"Invalid column: {column}")
                    return
                try:
                    if column in ['lat', 'lon', 'alt', 'temperature', 'relative_humidity', 'barometric_pressure', 'voltage', 'battery_level', 'rssi', 'snr']:
                        value = float(value)
                    elif column in ['node_number']:
                        value = int(value)
                    elif column in ['freeze']:
                        value = value.lower() in ['1', 'true', 'yes', 'on']
                except Exception:
                    pass
                if getattr(node, 'freeze', False) and column != 'freeze':
                    logging.info(f"Node {node_id} is frozen. Only the 'freeze' column can be modified until it is unset.")
                    return
                kwargs = dict(node_number=node.node_number)
                for k in valid_columns:
                    if k != 'id':
                        kwargs[k] = getattr(node, k)
                if isinstance(value, (float, bool)):
                    kwargs[column] = value
                else:
                    try:
                        kwargs[column] = ast.literal_eval(value)
                    except Exception:
                        kwargs[column] = value
                db.add_or_update_node(**kwargs)
                logging.info(f"Set {column} to {value} for node {node_id}")
            elif args.nodes_action == 'packet':
                node_id = getattr(args, 'node_id', None)
                with db._db_lock:
                    session = db.get_session()
                    try:
                        if node_id:
                            packets = db.get_node_packet(node_id)
                        else:
                            packets = session.query(NodePacket).order_by(NodePacket.timestamp.desc()).limit(1000).all()
                        # Preload gateway node_id mapping
                        gateway_ids = {}
                        gateway_dbids = set(pkt.gateway_node_id for pkt in packets if pkt.gateway_node_id)
                        if gateway_dbids:
                            nodes = session.query(Node).filter(Node.id.in_(gateway_dbids)).all()
                            gateway_ids = {n.id: n.node_id for n in nodes}
                    finally:
                        session.close()
                if not packets:
                    print("No packet found" + (f" for node {node_id}" if node_id else ""))
                    return
                packet_table = []
                for pkt in packets:
                    gateway_node_id_str = gateway_ids.get(pkt.gateway_node_id, str(pkt.gateway_node_id) if pkt.gateway_node_id else '-')
                    packet_table.append({
                        'timestamp': pkt.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        'from_node_id': pkt.from_node_id,
                        'gateway_node_id': gateway_node_id_str,
                        'to_node_id': pkt.to_node_id,
                        'packet_type': pkt.packet_type,
                        'payload_size': pkt.payload_size,
                        'success': pkt.success,
                        'channel_id': pkt.channel_id,
                        'packet_id': pkt.packet_id,
                        'rx_rssi': pkt.rx_rssi,
                        'rx_snr': pkt.rx_snr,
                        'rx_time': pkt.rx_time,
                        'hop_start': pkt.hop_start,
                        'hop_limit': pkt.hop_limit
                    })
                # Sorting logic for packet table
                sort_col = getattr(args, 'sort', None) or 'timestamp'
                col_map = {
                    'timestamp': 'timestamp',
                    'from': 'from_node_id',
                    'from_node_id': 'from_node_id',
                    'gateway': 'gateway_node_id',
                    'gateway_node_id': 'gateway_node_id',
                    'to': 'to_node_id',
                    'to_node_id': 'to_node_id',
                    'type': 'packet_type',
                    'packet_type': 'packet_type',
                    'size': 'payload_size',
                    'payload_size': 'payload_size',
                    'success': 'success',
                    'channel id': 'channel_id',
                    'channel_id': 'channel_id',
                    'packet id': 'packet_id',
                    'packet_id': 'packet_id',
                    'rx rssi': 'rx_rssi',
                    'rx_rssi': 'rx_rssi',
                    'rx snr': 'rx_snr',
                    'rx_snr': 'rx_snr',
                    'rx time': 'rx_time',
                    'rx_time': 'rx_time',
                    'hop start': 'hop_start',
                    'hop_start': 'hop_start',
                    'hop limit': 'hop_limit',
                    'hop_limit': 'hop_limit',
                }
                sort_col_key = col_map.get(sort_col.lower().replace(' ', '_'), sort_col.lower().replace(' ', '_'))
                if sort_col_key not in packet_table[0]:
                    sort_col_key = 'timestamp'
                # Show recents at the bottom if sorting by timestamp
                reverse_sort = sort_col_key != 'timestamp'
                packet_table.sort(key=lambda x: (x[sort_col_key] if x[sort_col_key] is not None else '' if isinstance(x[sort_col_key], str) else float('-inf')), reverse=reverse_sort)
                print_table(packet_table, headers=['Timestamp', 'From', 'Gateway', 'To', 'Type', 'Size', 'Success', 'Channel ID', 'Packet ID', 'RX RSSI', 'RX SNR', 'RX Time', 'Hop Start', 'Hop Limit'])
            elif args.nodes_action == 'activity':
                # --- ACTIVITY TABLE LOGIC ---
                minutes = getattr(args, 'minutes', None)
                node_id_filter = getattr(args, 'node_id', None)
                if minutes is None:
                    print("Debes especificar el número de minutos para el cálculo de métricas.")
                    return
                with db._db_lock:
                    session = db.get_session()
                    try:
                        time_limit = datetime.now() - timedelta(minutes=int(minutes))
                        query = session.query(NodePacket).filter(NodePacket.timestamp >= time_limit)
                        if node_id_filter:
                            node = session.query(Node).filter(Node.node_id == node_id_filter).first()
                            if not node:
                                print(f"Node {node_id_filter} not found.")
                                return
                            query = query.filter(
                                (NodePacket.from_node_id == node.node_id) | (NodePacket.to_node_id == node.node_id)
                            )
                        packets = query.all()
                        # --- Build metrics for all nodes ---
                        metrics = {}
                        for pkt in packets:
                            # For both sender and receiver, count packets and successes/fails
                            for direction, node_id in [('from', pkt.from_node_id), ('to', pkt.to_node_id)]:
                                if node_id is None:
                                    continue
                                node_obj = session.query(Node).filter(Node.node_id == node_id).first()
                                if not node_obj:
                                    continue
                                if node_id not in metrics:
                                    metrics[node_id] = {
                                        'packets_from': 0,
                                        'packets_to': 0,
                                        'success_from': 0,
                                        'fail_from': 0,
                                        'success_to': 0,
                                        'fail_to': 0,
                                        'short_name': node_obj.short_name if node_obj else '-',
                                        'long_name': node_obj.long_name if node_obj else '-',
                                    }
                                if direction == 'from':
                                    metrics[node_id]['packets_from'] += 1
                                    if pkt.success is True:
                                        metrics[node_id]['success_from'] += 1
                                    elif pkt.success is False:
                                        metrics[node_id]['fail_from'] += 1
                                elif direction == 'to':
                                    metrics[node_id]['packets_to'] += 1
                                    if pkt.success is True:
                                        metrics[node_id]['success_to'] += 1
                                    elif pkt.success is False:
                                        metrics[node_id]['fail_to'] += 1
                        # --- Table for all nodes ---
                        if not node_id_filter:
                            activity_table = []
                            for node_id, data in metrics.items():
                                packets_from = data['packets_from']
                                packets_to = data['packets_to']
                                # Calculate success rates, ignoring None values for success
                                success_from_count = data['success_from']
                                fail_from_count = data.get('fail_from', 0)
                                total_from = success_from_count + fail_from_count
                                if total_from:
                                    success_rate_from = f"{int(round((success_from_count / total_from) * 100))}%"
                                else:
                                    success_rate_from = '-'

                                success_to_count = data['success_to']
                                fail_to_count = data.get('fail_to', 0)
                                total_to = success_to_count + fail_to_count
                                if total_to:
                                    success_rate_to = f"{int(round((success_to_count / total_to) * 100))}%"
                                else:
                                    success_rate_to = '-'

                                activity_table.append({
                                    'Node ID': node_id,
                                    'Short Name': data['short_name'],
                                    'Long Name': data['long_name'],
                                    'Packets From': packets_from,
                                    'Packets To': packets_to,
                                    'Success Rate From': success_rate_from,
                                    'Success Rate To': success_rate_to,
                                })
                            sort_col = getattr(args, 'sort', None) or 'Packets From'
                            sort_col_key = sort_col.lower().replace(' ', '_')
                            valid_keys = {k.lower().replace(' ', '_'): k for k in activity_table[0].keys()}
                            if sort_col_key not in valid_keys:
                                sort_col_key = 'packets_from'
                            real_key = valid_keys[sort_col_key]
                            activity_table.sort(key=lambda x: (x[real_key] if x[real_key] is not None else float('-inf')), reverse=True)
                            print_table(activity_table, headers=['Node ID', 'Short Name', 'Long Name', 'Packets From', 'Packets To', 'Success Rate From', 'Success Rate To'])
                        # --- Table for single node ---
                        else:
                            node_id = node_id_filter
                            data = metrics.get(node_id)
                            if not data:
                                print(f"No activity found for node {node_id}")
                                return
                            packets_from = data['packets_from']
                            packets_to = data['packets_to']
                            # For single node
                            success_from_count = data['success_from']
                            fail_from_count = data.get('fail_from', 0)
                            total_from = success_from_count + fail_from_count
                            if total_from:
                                success_rate_from = f"{int(round((success_from_count / total_from) * 100))}%"
                            else:
                                success_rate_from = '-'

                            success_to_count = data['success_to']
                            fail_to_count = data.get('fail_to', 0)
                            total_to = success_to_count + fail_to_count
                            if total_to:
                                success_rate_to = f"{int(round((success_to_count / total_to) * 100))}%"
                            else:
                                success_rate_to = '-'

                            single_node_activity_table = [{
                                'Node ID': node_id,
                                'Short Name': data['short_name'],
                                'Long Name': data['long_name'],
                                'Packets From': packets_from,
                                'Packets To': packets_to,
                                'Success Rate From': success_rate_from,
                                'Success Rate To': success_rate_to,
                            }]
                            print_table(single_node_activity_table, headers=['Node ID', 'Short Name', 'Long Name', 'Packets From', 'Packets To', 'Success Rate From', 'Success Rate To'])
                    finally:
                        session.close()
            # --- ACTIVITY TABLE LOGIC ---
            elif args.nodes_action == 'activity':
                # For all nodes: show Packets From, Packets To, Success Rate From, Success Rate To
                def get_activity_stats(node_id):
                    # Returns (packets_from, packets_to, success_rate_from, success_rate_to)
                    packets_from = DB.count_packets(from_node_id=node_id)
                    packets_to = DB.count_packets(to_node_id=node_id)
                    success_from = DB.count_packets(from_node_id=node_id, success=True)
                    success_to = DB.count_packets(to_node_id=node_id, success=True)
                    success_rate_from = (success_from / packets_from) if packets_from else 0.0
                    success_rate_to = (success_to / packets_to) if packets_to else 0.0
                    return packets_from, packets_to, success_rate_from, success_rate_to

                # For all nodes activity table
                activity_table = []
                for node in nodes:
                    packets_from, packets_to, success_rate_from, success_rate_to = get_activity_stats(node.node_id)
                    activity_table.append({
                        'Node ID': node.node_id,
                        'Packets From': packets_from,
                        'Packets To': packets_to,
                        'Success Rate From': f"{success_rate_from:.2%}",
                        'Success Rate To': f"{success_rate_to:.2%}",
                        'Short Name': node.short_name,
                        'Long Name': node.long_name,
                    })
                print_table(activity_table, headers=['Node ID', 'Packets From', 'Packets To', 'Success Rate From', 'Success Rate To', 'Short Name', 'Long Name'])
            # --- SINGLE NODE ACTIVITY LOGIC ---
            elif args.nodes_action == 'activity':
                node_id = args.node_id
                node = None
                try:
                    node_number = int(node_id)
                    node = db.get_node(node_number)
                except ValueError:
                    for n in db.get_all_nodes():
                        if n.node_mac == node_id:
                            node = n
                            break
                if not node:
                    logging.info(f"Node not found: {node_id}")
                    return
                # Para una sola nodo: usar el mismo cálculo que para todos, pero mostrar solo uno
                packets_from, packets_to, success_rate_from, success_rate_to = DB.get_activity_stats(node_id)
                single_node_activity_table = [{
                    'Packets From': packets_from,
                    'Packets To': packets_to,
                    'Success Rate From': f"{success_rate_from:.2%}",
                    'Success Rate To': f"{success_rate_to:.2%}",
                    'Short Name': node.short_name,
                    'Long Name': node.long_name,
                }]
                print_table(single_node_activity_table, headers=['Packets From', 'Packets To', 'Success Rate From', 'Success Rate To', 'Short Name', 'Long Name'])
        elif getattr(args, 'db_action', None) == 'channels':
            if args.channels_action == 'list':
                channels = db.get_all_channels()
                channel_table = []
                for channel in channels:
                    members_count = len(channel.member_nodes) if channel.member_nodes else 0
                    channel_table.append({
                        'channel_num': channel.channel_num,
                        'channel_id': channel.channel_id,
                        'aes_key': channel.aes_key,
                        'members': members_count
                    })
                if channel_table:
                    print_table(channel_table, headers=['Channel Number', 'Channel ID', 'AES Key', 'Members'])
            elif args.channels_action == 'activity':
                # Show channel table with Packets and Bytes columns
                channels = db.get_all_channels()
                channel_table = []
                with db._db_lock:
                    session = db.get_session()
                    try:
                        # Get all packets, group by channel_id
                        packets = session.query(NodePacket).all()
                        channel_stats = {}
                        for pkt in packets:
                            if pkt.channel_id is None:
                                continue
                            if pkt.channel_id not in channel_stats:
                                channel_stats[pkt.channel_id] = {'packets': 0, 'bytes': 0}
                            channel_stats[pkt.channel_id]['packets'] += 1
                            if pkt.payload_size:
                                channel_stats[pkt.channel_id]['bytes'] += pkt.payload_size
                        for channel in channels:
                            members_count = len(channel.member_nodes) if channel.member_nodes else 0
                            stats = channel_stats.get(channel.channel_id, {'packets': 0, 'bytes': 0})
                            channel_table.append({
                                'channel_num': channel.channel_num,
                                'channel_id': channel.channel_id,
                                'aes_key': channel.aes_key,
                                'members': members_count,
                                'packets': stats['packets'],
                                'bytes': stats['bytes']
                            })
                    finally:
                        session.close()
                if channel_table:
                    print_table(channel_table, headers=['Channel Number', 'Channel ID', 'AES Key', 'Members', 'Packets', 'Bytes'])
            elif args.channels_action == 'show':
                channel_id = args.channel_id
                channel = None
                for c in db.get_all_channels():
                    if c.channel_id == channel_id:
                        channel = c
                        break
                if not channel:
                    logging.info(f"Channel not found: {channel_id}")
                    return
                members_count = len(channel.member_nodes) if channel.member_nodes else 0
                # --- Enhanced channel stats ---
                with db._db_lock:
                    session = db.get_session()
                    try:
                        packets = session.query(NodePacket).filter(NodePacket.channel_id == channel.channel_id).all()
                        total_sent_packets = len(packets)
                        total_sent_bytes = sum(pkt.payload_size or 0 for pkt in packets)
                        # Packet count by types
                        type_counts = {}
                        for pkt in packets:
                            t = pkt.packet_type or '-'
                            type_counts[t] = type_counts.get(t, 0) + 1
                        # Packet ratio by types
                        type_ratios = {t: (count / total_sent_packets if total_sent_packets else 0) for t, count in type_counts.items()}
                    finally:
                        session.close()
                # Prepare main channel info table
                channel_info = [{
                    'channel_num': channel.channel_num,
                    'channel_id': channel.channel_id,
                    'aes_key': channel.aes_key,
                    'members': members_count,
                    'total_sent_packets': total_sent_packets,
                    'total_sent_bytes': total_sent_bytes,
                }]
                print_table(channel_info, headers=['Channel Number', 'Channel ID', 'AES Key', 'Members', 'Total Sent Packets', 'Total Sent Bytes'])
                # --- Per-node packet type ratios table ---
                if total_sent_packets > 0:
                    # Build per-node stats: node_id -> {type: count, ...}
                    node_type_counts = {}
                    node_type_totals = {}
                    node_names = {}
                    for pkt in packets:
                        node_id = pkt.from_node_id
                        if node_id is None:
                            continue
                        t = pkt.packet_type or '-'
                        if node_id not in node_type_counts:
                            node_type_counts[node_id] = {}
                            node_type_totals[node_id] = 0
                            # Fetch node short/long name
                            node_obj = None
                            try:
                                with db._db_lock:
                                    session2 = db.get_session()
                                    node_obj = session2.query(Node).filter(Node.node_id == node_id).first()
                                    session2.close()
                            except Exception:
                                node_obj = None
                            node_names[node_id] = {
                                'short_name': node_obj.short_name if node_obj else '-',
                                'long_name': node_obj.long_name if node_obj else '-'
                            }
                        node_type_counts[node_id][t] = node_type_counts[node_id].get(t, 0) + 1
                        node_type_totals[node_id] += 1
                    # Build node table
                    node_rows = []
                    all_types = sorted(type_counts.keys())
                    for node_id, type_count_dict in node_type_counts.items():
                        row = {
                            'Node ID': node_id,
                            'Short Name': node_names[node_id]['short_name'],
                            'Long Name': node_names[node_id]['long_name'],
                            'Total Packets': node_type_totals[node_id],
                        }
                        for t in all_types:
                            count = type_count_dict.get(t, 0)
                            ratio = count / node_type_totals[node_id] if node_type_totals[node_id] else 0
                            row[t] = f"{ratio:.2%}" if node_type_totals[node_id] else '-'
                        node_rows.append(row)
                    # Sort node_rows by Total Packets descending
                    node_rows.sort(key=lambda x: x['Total Packets'], reverse=True)
                    # Build headers
                    headers = ['Node ID', 'Short Name', 'Long Name', 'Total Packets'] + all_types
                    print_table(node_rows, headers=headers)
                # Show packet type counts (global)
                if type_counts:
                    type_count_table = []
                    for t, count in type_counts.items():
                        ratio = type_ratios[t]
                        type_count_table.append({
                            'Packet Type': t,
                            'Count': count,
                            'Ratio': f"{ratio:.2%}" if total_sent_packets else '-'
                        })
                    # Sort type_count_table by Count descending
                    type_count_table.sort(key=lambda x: x['Count'], reverse=True)
                    print_table(type_count_table, headers=['Packet Type', 'Count', 'Ratio'])
        elif getattr(args, 'db_action', None) == 'delete':
            logging.info("Deleting the database...")
            db.delete_database()
    if follow:
        try:
            while True:
                from src.utils import clear_screen
                clear_screen()
                run_once()
                time.sleep(10)
        except KeyboardInterrupt:
            print("\nStopped following.")
    else:
        run_once()
