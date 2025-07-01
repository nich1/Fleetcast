import argparse

from gui import run_gui
from settings import open_config

def main():
    parser = argparse.ArgumentParser(description="Fleetcast")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("run", help="Launch the GUI")
    subparsers.add_parser("config", help="Edit the config file")

    args = parser.parse_args()

    if args.command == "run":
        run_gui()
    elif args.command == "config":
        open_config()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()