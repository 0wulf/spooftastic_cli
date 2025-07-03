import logging
from src.parser import build_parser
from src.commands.sniffer import handle_sniffer_mode
from src.commands.send import handle_send_mode
from src.commands.db import handle_db_mode
from src.commands.spoofer import handle_spoofer_mode


def main():
    parser = build_parser()
    args = parser.parse_args()
    global DEBUG
    DEBUG = getattr(args, 'debug', False)
    logging.getLogger().setLevel(logging.DEBUG if DEBUG else logging.INFO)
    match args.mode:
        case 'sniffer':
            handle_sniffer_mode(args)
        case 'send':
            handle_send_mode(args)
        case 'db':
            handle_db_mode(args)
        case 'spoofer':
            handle_spoofer_mode(args)


if __name__ == "__main__":
    main()