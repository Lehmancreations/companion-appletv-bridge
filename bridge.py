"""Local HTTP bridge from Bitfocus Companion to an Apple TV, using pyatv.

Keeps one connection to the Apple TV open so button presses are instant.
Send GET or POST http://127.0.0.1:8765/<command>, e.g. /up, /select, /volume_up.
Run pair.py once first; it writes config.json next to this file.
"""
import argparse
import asyncio
import errno
import json
import logging
import os
import sys

import pyatv
from aiohttp import web
from pyatv.storage.file_storage import FileStorage

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(HERE, "config.json")

log = logging.getLogger("appletv-bridge")

COMMANDS = {
    "up": lambda a: a.remote_control.up(),
    "down": lambda a: a.remote_control.down(),
    "left": lambda a: a.remote_control.left(),
    "right": lambda a: a.remote_control.right(),
    "select": lambda a: a.remote_control.select(),
    "menu": lambda a: a.remote_control.menu(),
    "home": lambda a: a.remote_control.home(),
    "control_center": lambda a: a.remote_control.control_center(),
    "screensaver": lambda a: a.remote_control.screensaver(),
    "play_pause": lambda a: a.remote_control.play_pause(),
    "play": lambda a: a.remote_control.play(),
    "pause": lambda a: a.remote_control.pause(),
    "skip_forward": lambda a: a.remote_control.skip_forward(),
    "skip_backward": lambda a: a.remote_control.skip_backward(),
    "next": lambda a: a.remote_control.next(),
    "previous": lambda a: a.remote_control.previous(),
    "volume_up": lambda a: a.audio.volume_up(),
    "volume_down": lambda a: a.audio.volume_down(),
    "sleep": lambda a: a.power.turn_off(),
    "wake": lambda a: a.power.turn_on(),
}


def load_config(args):
    cfg = {"port": 8765, "bind": "127.0.0.1"}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            cfg.update(json.load(f))
    for key in ("device_id", "address", "port", "bind"):
        value = getattr(args, key)
        if value is not None:
            cfg[key] = value
    if not cfg.get("device_id"):
        raise SystemExit("No Apple TV configured. Run pair.py first (it writes config.json).")
    return cfg


class Bridge:
    def __init__(self, device_id, address):
        self.device_id = device_id
        self.address = address
        self.atv = None
        self.lock = asyncio.Lock()

    async def connect(self):
        loop = asyncio.get_running_loop()
        storage = FileStorage.default_storage(loop)
        await storage.load()
        hosts = [self.address] if self.address else None
        found = await pyatv.scan(loop, identifier=self.device_id, hosts=hosts, storage=storage)
        if not found:
            raise RuntimeError("Apple TV not found on the network" + await self.diagnose())
        self.atv = await pyatv.connect(found[0], loop, storage=storage)
        self.atv.listener = self
        log.info("connected to %s", found[0].name)

    async def diagnose(self):
        """Explain a failed scan by trying a plain TCP connection to the Apple TV's AirPlay port."""
        if not self.address:
            return ""
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(self.address, 7000), 3)
            writer.close()
            return f" ({self.address} answers on port 7000, so the network is fine; is the TV asleep or re-paired?)"
        except asyncio.TimeoutError:
            return f" ({self.address} didn't answer: check it's on and on the same network)"
        except OSError as ex:
            hint = ""
            if sys.platform == "darwin" and ex.errno in (errno.EHOSTUNREACH, errno.EPERM, errno.EACCES):
                hint = ("; macOS is probably blocking local network access: turn on Python in "
                        "System Settings > Privacy & Security > Local Network, then restart the bridge")
            return f" (connecting to {self.address} failed: {ex.strerror or ex}{hint})"

    # pyatv DeviceListener callbacks: drop the connection so the next press reconnects
    def connection_lost(self, exception):
        log.warning("connection lost: %s", exception)
        self.atv = None

    def connection_closed(self):
        log.info("connection closed")
        self.atv = None

    async def run(self, action):
        async with self.lock:
            for attempt in (1, 2):
                try:
                    if self.atv is None:
                        await self.connect()
                    return await action(self.atv)
                except Exception:
                    log.exception("command failed (attempt %d)", attempt)
                    if self.atv is not None:
                        self.atv.close()
                    self.atv = None
                    if attempt == 2:
                        raise


async def handle_command(request):
    name = request.match_info["cmd"]
    if name not in COMMANDS:
        return web.json_response({"error": f"unknown command {name}", "commands": sorted(COMMANDS)}, status=404)
    try:
        await request.app["bridge"].run(COMMANDS[name])
    except Exception as ex:
        return web.json_response({"error": str(ex)}, status=502)
    return web.json_response({"ok": name})


async def handle_launch(request):
    app_id = request.match_info["app"]
    try:
        await request.app["bridge"].run(lambda a: a.apps.launch_app(app_id))
    except Exception as ex:
        return web.json_response({"error": str(ex)}, status=502)
    return web.json_response({"ok": "launch", "app": app_id})


async def handle_apps(request):
    try:
        apps = await request.app["bridge"].run(lambda a: a.apps.app_list())
    except Exception as ex:
        return web.json_response({"error": str(ex)}, status=502)
    return web.json_response({"apps": sorted(({"name": x.name, "id": x.identifier} for x in apps),
                                             key=lambda x: (x["name"] or "").lower())})


async def handle_status(request):
    return web.json_response({"connected": request.app["bridge"].atv is not None,
                              "commands": sorted(COMMANDS),
                              "also": ["GET /apps", "/launch/<bundle id>"]})


def main():
    parser = argparse.ArgumentParser(description="HTTP bridge from Bitfocus Companion to an Apple TV")
    parser.add_argument("--device-id", dest="device_id", help="Apple TV identifier (default: from config.json)")
    parser.add_argument("--address", help="Apple TV IP address (default: from config.json)")
    parser.add_argument("--port", type=int, help="port to listen on (default 8765)")
    parser.add_argument("--bind", help="address to listen on (default 127.0.0.1; use 0.0.0.0 if Companion "
                                       "runs on a different computer)")
    args = parser.parse_args()
    cfg = load_config(args)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = web.Application()
    app["bridge"] = Bridge(cfg["device_id"], cfg.get("address"))
    app.router.add_get("/", handle_status)
    app.router.add_get("/apps", handle_apps)
    app.router.add_route("*", "/launch/{app}", handle_launch)
    app.router.add_route("*", "/{cmd}", handle_command)
    log.info("listening on http://%s:%s", cfg["bind"], cfg["port"])
    web.run_app(app, host=cfg["bind"], port=cfg["port"], print=None)


if __name__ == "__main__":
    main()
