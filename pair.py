"""Find an Apple TV on the network, pair with it, and save config.json for bridge.py.

Usage:
    python pair.py                      # scan, pick an Apple TV, type the PIN shown on the TV
    python pair.py --address 192.168.1.50
    python pair.py --pin-file pin.txt   # wait for the PIN to be written to a file instead of typed

The pairing key is saved by pyatv in ~/.pyatv.conf (never share that file).
"""
import argparse
import asyncio
import json
import os
import sys

import pyatv
from pyatv.const import OperatingSystem, Protocol
from pyatv.storage.file_storage import FileStorage

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(HERE, "config.json")


def choose(devices):
    if len(devices) == 1:
        return devices[0]
    print("Apple TVs found:")
    for n, d in enumerate(devices, 1):
        print(f"  {n}. {d.name} ({d.address})")
    while True:
        pick = input(f"Which one (1-{len(devices)})? ").strip()
        if pick.isdigit() and 1 <= int(pick) <= len(devices):
            return devices[int(pick) - 1]


async def get_pin(pin_file):
    if not pin_file:
        return input("Enter the PIN shown on the TV: ").strip()
    print(f"Waiting for the PIN to be written to {pin_file} ...", flush=True)
    for _ in range(300):
        if os.path.exists(pin_file):
            with open(pin_file) as f:
                pin = f.read().strip()
            if pin:
                os.remove(pin_file)
                return pin
        await asyncio.sleep(1)
    raise SystemExit("Timed out waiting for the PIN")


async def main(args):
    loop = asyncio.get_running_loop()
    storage = FileStorage.default_storage(loop)
    await storage.load()

    print("Scanning the network for Apple TVs ...")
    hosts = [args.address] if args.address else None
    found = await pyatv.scan(loop, hosts=hosts, storage=storage, timeout=5)
    devices = [d for d in found
               if d.device_info.operating_system == OperatingSystem.TvOS and d.get_service(Protocol.Companion)]
    if not devices:
        print("No Apple TV found.")
        print("- Make sure it's on and on the same network as this computer.")
        print("- On macOS, the app running this (Terminal, iTerm...) needs Local Network access:")
        print("  System Settings > Privacy & Security > Local Network.")
        print("- Or try again with --address <the Apple TV's IP address>.")
        sys.exit(1)
    atv = choose(devices)
    print(f"Pairing with {atv.name} ({atv.address}). A PIN will appear on the TV.")

    pairing = await pyatv.pair(atv, Protocol.Companion, loop, storage=storage)
    try:
        await pairing.begin()
        pairing.pin(await get_pin(args.pin_file))
        await pairing.finish()
        paired = pairing.has_paired
    finally:
        await pairing.close()
    if not paired:
        raise SystemExit("Pairing failed. Run pair.py again and check the PIN.")
    await storage.save()

    cfg = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
    cfg.update({"device_id": atv.identifier, "address": str(atv.address), "name": atv.name})
    cfg.setdefault("port", 8765)
    cfg.setdefault("bind", "127.0.0.1")
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"Paired. Saved {CONFIG_FILE}")
    print("Next: start the bridge (see README) and test it with  curl http://127.0.0.1:8765/right")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pair with an Apple TV for bridge.py")
    parser.add_argument("--address", help="Apple TV IP address (skips network discovery)")
    parser.add_argument("--pin-file", help="read the PIN from this file instead of typing it")
    asyncio.run(main(parser.parse_args()))
