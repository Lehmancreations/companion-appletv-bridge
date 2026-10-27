# Companion Apple TV Bridge

Control an Apple TV from [Bitfocus Companion](https://bitfocus.io/companion) and a Stream Deck: arrows, Select, Menu, Home, Play/Pause, skip, volume, Control Center, sleep/wake, and launching apps.

It's a small Python service built on [pyatv](https://pyatv.dev). It talks to the Apple TV the same way Apple's own Remote app does, and gives Companion simple web addresses to call:

```
Stream Deck → Companion → http://127.0.0.1:8765/select → bridge.py → Apple TV
```

The bridge keeps one connection to the Apple TV open, so after the first press each button responds in about 50 ms.

Works with Companion on **macOS, Windows, Linux and Raspberry Pi** (including CompanionPi).

> **Tested so far:** the bridge, pairing and the Companion 5.0 page on macOS with an Apple TV 4K (tvOS 26). The Windows and Linux/Raspberry Pi installers are new and haven't been run on real hardware yet. If you try one, please open an issue saying whether it worked.

---

## What you need

- An Apple TV (HD or 4K) on the same network as the computer that will run the bridge. Usually that's the same computer that runs Companion.
- **Python 3.9 or newer** on that computer. The Linux installer adds what's missing on Raspberry Pi OS.
- **Companion 5.x** to import the ready-made button page. On Companion 3.x or 4.x, make the buttons by hand instead; see [Older Companion versions](#older-companion-versions).

## 1. Download

Click **Code → Download ZIP** on this page and unzip it somewhere permanent, for example your home folder. Or clone it:

```
git clone https://github.com/lehmancreations/companion-appletv-bridge.git
cd companion-appletv-bridge
```

Don't move the folder after installing; the startup service points at it.

## 2. Install and pair

Turn the Apple TV on and keep it where you can see it. The installer finds the Apple TV, shows a 4-digit PIN on the TV, and asks you to type it in. It then sets the bridge to start automatically.

### macOS

Open **Terminal**, go to the folder, and run:

```
bash install/macos/install.sh
```

- macOS may ask to allow **Terminal** and **Python** to find devices on your local network. Click **Allow** both times.
- If it says *No Apple TV found* or *No route to host*, open **System Settings → Privacy & Security → Local Network**, turn on Terminal (or whatever app you ran it from), and run the installer again.
- It installs a LaunchAgent (`com.companion.appletv-bridge`) that starts the bridge when you log in. The log is `bridge.log` in the folder.

### Windows

Open **PowerShell** in the folder (in the folder: Shift + right-click → *Open PowerShell window here*) and run:

```
powershell -ExecutionPolicy Bypass -File install\windows\install.ps1
```

- Install Python from [python.org](https://www.python.org/downloads/windows/) first and tick **Add python.exe to PATH**.
- If Windows Firewall asks about Python, allow it on **Private** networks.
- It registers a scheduled task, *Apple TV Bridge for Companion*, that starts the bridge in the background when you log in.

### Linux and Raspberry Pi

SSH in (or open a terminal) as your normal user, not root, go to the folder, and run:

```
bash install/linux/install.sh
```

- It installs `python3-venv` if it's missing, and creates a systemd service `appletv-bridge` that starts at boot.
- Logs: `journalctl -u appletv-bridge -f`

### Check it works

Watch the TV and run:

```
curl http://127.0.0.1:8765/right
```

On Windows, use `Invoke-RestMethod http://127.0.0.1:8765/right` instead. The highlight on the TV should move one step right, and you should see `{"ok": "right"}`.

## 3. Add the buttons to Companion

1. In Companion, go to **Import / Export → Import configuration** and choose `companion/apple-tv-page.companionconfig`.
2. Pick a **destination page**. It defaults to page 1, so change it to an empty page.
3. Under *Import Connections Behavior*, choose either option for **appletv-bridge**:
   - **[ Create new connection ]**: adds a Generic HTTP connection with no settings to fill in.
   - **Link to** an HTTP connection you already have: Companion picks this automatically if you have one, and it works too, because the buttons use full `http://` addresses, which skip that connection's URL prefix.
4. Click **Replace page N with imported page**.

You get 15 buttons:

| | |
|---|---|
| Arrows + Select | Up, Down, Left, Right, Select |
| Navigation | Menu/Back, Home, Control Center |
| Playback | Play/Pause, Skip Back, Skip Fwd |
| Volume | Vol +, Vol − (works when the Apple TV controls the volume, e.g. HDMI-CEC or a HomePod) |
| Power | Wake, Sleep |

**Bridge on a different computer, a different port, or a different text size?** Rebuild the page file first:

```
python3 companion/build_page.py --host 192.168.1.20 --port 8765 --text-size 28
```

## Making your own buttons

Any Companion button can call the bridge. Add a **Generic HTTP → GET** action with one of these URLs:

| URL | Does |
|---|---|
| `http://127.0.0.1:8765/up` (`down`, `left`, `right`, `select`) | Arrows and Select |
| `/menu`, `/home`, `/control_center`, `/screensaver` | Navigation |
| `/play_pause`, `/play`, `/pause`, `/skip_forward`, `/skip_backward`, `/next`, `/previous` | Playback |
| `/volume_up`, `/volume_down` | Volume |
| `/wake`, `/sleep` | Power |
| `/launch/<app id>` | Open an app, e.g. `/launch/com.netflix.Netflix` |
| `/apps` | List installed apps and their IDs (open it in a browser) |
| `/` | Status and the list of commands |

POST works too, if your HTTP connection is set up that way.

## Companion on a different computer

The bridge only listens to its own computer by default (`127.0.0.1`), which is the safe choice. If Companion runs on another computer:

1. In `config.json`, set `"bind": "0.0.0.0"`, then restart the bridge (or rerun the installer).
2. Rebuild the page with `--host <bridge computer's IP>` and import it.

The bridge has **no password**, so anyone on your network could send commands to the TV. Only do this on a network you trust.

## Troubleshooting

| Problem | Fix |
|---|---|
| *No Apple TV found* | Make sure it's on and on the same network (same Wi-Fi / VLAN). On macOS, check the Local Network permission (above). Or pass the IP: `.venv/bin/python pair.py --address 192.168.1.50`. |
| Pairing failed | Check the PIN and try again. After a few wrong PINs the Apple TV makes you wait before it lets you try again. |
| macOS: the installer says the bridge is running, but commands return *Apple TV not found* | macOS is blocking the background service from the local network. Turn on **Python** in System Settings → Privacy & Security → Local Network. Wait a minute, then restart the bridge with `launchctl kickstart -k gui/$(id -u)/com.companion.appletv-bridge`. The setting can take a minute to apply, so if the first restart still fails, try again. |
| Buttons do nothing | Run the `curl` test above. If it fails, the bridge isn't running; check its log. If it works, check the button's URL and that Companion's HTTP connection is enabled. |
| Worked, then stopped after the Apple TV was reset or replaced | Delete `config.json` and run the installer again to pair again. |
| Volume buttons don't change the volume | The bridge can only change the volume when the Apple TV itself controls it: over HDMI-CEC, or through AirPlay speakers such as a HomePod. If your Siri Remote changes the TV's volume with infrared (IR), the remote talks straight to the TV and the Apple TV never sees it, so volume can't work over the network. The volume buttons still return `ok`, because the TV gives no way to tell whether the volume changed. |

The pairing key is saved by pyatv in `~/.pyatv.conf` (on Windows, `C:\Users\<you>\.pyatv.conf`). Keep it private; it lets that computer control your Apple TV. To revoke it, remove the computer from the Apple TV's list of paired remote devices in Settings.

## Uninstall

- **macOS:** `launchctl bootout gui/$(id -u)/com.companion.appletv-bridge; rm ~/Library/LaunchAgents/com.companion.appletv-bridge.plist`
- **Windows:** `Unregister-ScheduledTask -TaskName "Apple TV Bridge for Companion" -Confirm:$false`
- **Linux/Pi:** `sudo systemctl disable --now appletv-bridge; sudo rm /etc/systemd/system/appletv-bridge.service`

Then delete the folder, and `~/.pyatv.conf` if nothing else uses pyatv.

## Running it by hand

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt          # Windows: .venv\Scripts\pip
.venv/bin/python pair.py                           # once
.venv/bin/python bridge.py                         # --port, --bind, --address, --device-id to override config.json
```

## Credits

Built on [pyatv](https://github.com/postlund/pyatv) by Pierre Ståhl (MIT). Not affiliated with Apple or Bitfocus.
Forked from (https://github.com/sempei13/companion-appletv-bridge) because his was not working on my computer

## License

MIT. See [LICENSE](LICENSE).
