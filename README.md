# ws-ephemeral

Automates setting up ephemeral ports on Windscribe VPN for port forwarding. Designed for use with qBittorrent behind Gluetun VPN.

## What It Does

1. **Health check** - Verifies both qBittorrent and Gluetun are accessible
2. **Creates ephemeral port** on Windscribe - obtains a random port for inbound connections
3. **Updates qBittorrent** - configures the torrent client's listen port to match
4. **Notifies Gluetun** - tells the VPN container to forward the port through the tunnel
5. **Repeats weekly** - runs on a schedule to renew the port before it expires

## Quick Start

```bash
# 1. Get your session cookie (see below)
# 2. Copy and configure .env
cp .env.example .env

# 3. Run with Docker Compose
docker compose up -d
```

## Authentication

Windscribe uses Cloudflare protection which blocks automated login. Use a session cookie instead:

1. Log into [windscribe.com](https://windscribe.com) in your browser
2. Install a cookie export extension (e.g., EditThisCookie, Cookie-Editor)
3. Find the `ws_session_auth_hash` cookie
4. Copy its value and set as `WS_SESSION_COOKIE` environment variable

```bash
WS_SESSION_COOKIE=1194783%3A1%3A1774370088%3A...
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WS_SESSION_COOKIE` | Your `ws_session_auth_hash` cookie from browser | - |
| `OPENVPN_USER` | Windscribe VPN username (for Gluetun) | - |
| `OPENVPN_PASSWORD` | Windscribe VPN password (for Gluetun) | - |
| `SERVER_CITIES` | VPN server location (e.g., Brussels) | - |
| `QBIT_HOST` | qBittorrent web UI address | 127.0.0.1 |
| `QBIT_PORT` | qBittorrent web UI port | 8080 |
| `QBIT_USERNAME` | qBittorrent web UI username | - |
| `QBIT_PASSWORD` | qBittorrent web UI password | - |
| `QBIT_PRIVATE_TRACKER` | Disable DHT/PeX/LSD (true/false) | false |
| `GLUETUN_HOST` | Gluetun control server hostname | localhost |
| `GLUETUN_PORT` | Gluetun control server port | 8000 |
| `GLUETUN_AUTH_TYPE` | Auth type: none, basic, or apikey | No |
| `GLUETUN_API_KEY` | Gluetun API key | No |
| `DAYS` | Days between port renewal (default: 6) | No |
| `TIME` | Time of day to run (default: 02:00) | No |
| `ONESHOT` | Run once and exit (true/false) | No |
| `WS_DEBUG` | Enable debug logging (true/false) | No |
| `REQUEST_TIMEOUT` | HTTP timeout in seconds (default: 5) | No |

## Docker Compose Example

```yaml
version: "3.8"

services:
  gluetun:
    image: qmcgaw/gluetun:latest
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun:/dev/net/tun
    environment:
      - VPN_SERVICE_PROVIDER=windscribe
      - VPN_TYPE=openvpn
      - OPENVPN_USER=${OPENVPN_USER}
      - OPENVPN_PASSWORD=${OPENVPN_PASSWORD}
      - SERVER_CITIES=${SERVER_CITIES}
      - FIREWALL_VPN_INPUT_PORTS=10412
      - HTTP_CONTROL_SERVER_AUTH_DEFAULT_ROLE={"auth":"apikey","apikey":"${GLUETUN_API_KEY}"}
    ports:
      - "8000:8000"
    volumes:
      - gluetun_data:/gluetun
    restart: unless-stopped

  qbittorrent:
    image: lscr.io/linuxserver/qbittorrent:latest
    network_mode: service:gluetun
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/London
      - WEBUI_PORT=8080
      - TORRENTING_PORT=10412
    volumes:
      - qbittorrent_config:/config
      - /path/to/downloads:/downloads
    depends_on:
      - gluetun
    restart: unless-stopped

  ws-ephemeral:
    image: ws-ephemeral
    environment:
      - WS_SESSION_COOKIE=${WS_SESSION_COOKIE}
      - QBIT_HOST=localhost
      - QBIT_PORT=8080
      - QBIT_USERNAME=${QBIT_USERNAME}
      - QBIT_PASSWORD=${QBIT_PASSWORD}
      - QBIT_PRIVATE_TRACKER=true
      - GLUETUN_HOST=gluetun
      - GLUETUN_PORT=8000
      - GLUETUN_AUTH_TYPE=apikey
      - GLUETUN_API_KEY=${GLUETUN_API_KEY}
      - DAYS=6
      - TIME=02:00
    depends_on:
      - gluetun
      - qbittorrent
    restart: unless-stopped

volumes:
  gluetun_data:
  qbittorrent_config:
```

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network                          │
│                                                             │
│   ┌─────────────┐      ┌──────────────┐                     │
│   │  qBittorrent│ ───► │    Gluetun   │ ───► Internet      │
│   │   (port     │      │  (VPN tunnel)│                     │
│   │   10412)    │      │   (port      │                     │
│   └─────────────┘      │   forward)   │                     │
│        ▲              └──────────────┘                     │
│        │                     ▲                             │
│        │                     │                             │
│   ┌────┴────┐           ┌────┴────┐                       │
│   │ ws-     │           │ Control  │                       │
│   │ ephemeral│           │  API     │                       │
│   └─────────┘           └──────────┘                       │
└─────────────────────────────────────────────────────────────┘

1. ws-ephemeral connects to Windscribe API using session cookie
2. Creates ephemeral port (e.g., 10291)
3. Updates qBittorrent's listen port to match
4. Notifies Gluetun to forward the port through VPN tunnel
```

## Running Locally (Without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your credentials

# Run once
python -m src.run

# Or run as daemon (default: every 6 days at 02:00)
python -m src.run
```

## License

GPL-3.0 - See [LICENSE.md](LICENSE.md)