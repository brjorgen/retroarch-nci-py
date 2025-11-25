#!/usr/bin/env python3

"""
This script connects to a running RetroArch instance.
NCI (also known as "network commands") must be enabled.
"""

import argparse
from retroarch_nci import RetroArchNCI, NCICommand

def list_commands():
    print("Available NCI commands:")
    for cmd in NCICommand:
        print(f"- {cmd.name}")


def main():
    parser = argparse.ArgumentParser(description="RetroArch NCI CLI")
    parser.add_argument("--host", default="127.0.0.1", help="RetroArch host")
    parser.add_argument("--port", type=int, default=55355, help="RetroArch NCI UDP port")
    args = parser.parse_args()

    nci = RetroArchNCI(host=args.host, port=args.port)

    print(f"Connected to RetroArch NCI at {args.host}:{args.port}")
    print("Type 'help' to list commands, 'exit' to quit.")

    while True:
        try:
            cmd_input = input("RetroArchNCI > ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

        if not cmd_input:
            continue

        if cmd_input.lower() in ("!exit", "!quit"):
            break

        if cmd_input.lower() in ("help", "?"):
            list_commands()
            continue

        parts = cmd_input.split()
        cmd_name = parts[0].upper()
        args_list = parts[1:]

        try:
            cmd_enum = NCICommand[cmd_name]
            resp = nci.cmd(cmd_enum, *args_list)

        except KeyError:
            # fallback: treat as raw string
            resp = nci.send_nci_command(cmd_name, *args_list)

        if resp is None:
            print("[No response / timeout]")

        else:
            print(resp)


if __name__ == "__main__":
    main()
