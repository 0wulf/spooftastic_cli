from src.agents.spoofer import Spoofer
from settings import BROADCAST_MAC

def handle_spoofer_mode(args):
    spoofer = Spoofer()
    spoof_mode = getattr(args, 'spoof_mode', None)
    # Build kwargs for spoofing methods, but do NOT include restore_after (placeholder only)
    # Ensure burst and period are always int, not None or str
    burst = getattr(args, 'burst', 1)
    try:
        burst = int(burst)
    except (TypeError, ValueError):
        burst = 1
    period = getattr(args, 'period', 2)
    try:
        period = int(period)
    except (TypeError, ValueError):
        period = 2
    # Only include burst and period if not None and of correct type
    kwargs = dict(
        to_node=args.to_node,
        from_node=args.node_id,
        short_name=getattr(args, 'short_name', None),
        long_name=getattr(args, 'long_name', None),
        hw_model=getattr(args, 'hw_model', None),
        lat=getattr(args, 'lat', None),
        lon=getattr(args, 'lon', None),
        alt=getattr(args, 'alt', None),
        pubkey=getattr(args, 'pubkey', None),
        gateway_node=getattr(args, 'gateway_node', BROADCAST_MAC),
    )
    if spoof_mode == 'reactive':
        spoofer.spoof_reactive(**kwargs, burst=burst, period=period)
    elif spoof_mode == 'periodic':
        interval = getattr(args, 'interval', 60)
        try:
            interval = int(interval)
        except (TypeError, ValueError):
            interval = 60
        spoofer.spoof_periodic(**kwargs, burst=burst, period=period, interval=interval)
    elif spoof_mode == 'hybrid':
        interval = getattr(args, 'interval', 60)
        try:
            interval = int(interval)
        except (TypeError, ValueError):
            interval = 60
        spoofer.spoof_hybrid(**kwargs, burst=burst, period=period, interval=interval)
    else:
        spoofer.spoof_node(**kwargs, burst=burst, period=period)
