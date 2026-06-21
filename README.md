# FireLabs for Home Assistant

A local Home Assistant integration for FireLabs smart plugs (Sonoff S31 running FireLabs firmware). It talks to the plug over its local HTTP API, so it needs no MQTT, no broker, and no cloud.

## Requirements

- A plug running FireLabs firmware, already on your wifi.
- Home Assistant 2024.4 or newer.

## Install (HACS)

1. In HACS, open the three-dot menu and choose **Custom repositories**.
2. Add `https://github.com/fireball1725/firelabs-hass` with category **Integration**.
3. Install **FireLabs**, then restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration**, search **FireLabs**, and enter the plug's IP address or `fl-<name>.local` hostname.

Plugs on your network are also found automatically: Home Assistant shows a "discovered" card and you just confirm, no address needed. The plug is identified by its MAC, so its IP can change without breaking the device or its history.

## Entities

| Entity | Type | Notes |
|---|---|---|
| Relay | switch | the outlet; primary control |
| Power, Voltage, Current, Energy today | sensor | metered S31 only |
| Fault | binary_sensor | relay on but drawing ~0 W |
| No-load indicator | switch | config; metered S31 only |
| Restore mode | select | Off / On / Last |
| Identify | switch | blink the LED to find the plug |
| WiFi signal, Uptime | sensor | diagnostic, disabled by default |
| Restart | button | reboot the plug |

On an S31 Lite (no power-metering chip) the power sensors, fault, and no-load entities are left out automatically.

## How it works

Home Assistant polls `GET /api/status` every 5 seconds and writes changes with `POST /api/relay`, `/api/config`, `/api/identify`, and `/api/restart`. Everything stays on your LAN.

## MQTT or this integration

The firmware also supports MQTT Discovery. Use one or the other, not both, to avoid two copies of the same entities. This integration is the path for setups that don't run MQTT.

## License

MIT
