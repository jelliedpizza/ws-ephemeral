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
2. Open your browser's Developer Tools (F12 or Right Click -> Inspect).
3. Navigate to the **Application** (Chrome) or **Storage** (Firefox) tab.
4. Expand the **Cookies** section for `windscribe.com`.
5. Find the cookie named `ws_session_auth_hash` and copy its value.
6. Set that value as your `WS_SESSION_COOKIE` environment variable.

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
| `QBIT_HOST` | qBittorrent web UI address | localhost |
| `QBIT_PORT` | qBittorrent web UI port | 8080 |
| `QBIT_USERNAME` | qBittorrent web UI username | default123!! |
| `QBIT_PASSWORD` | qBittorrent web UI password | default123!! |
| `QBIT_PRIVATE_TRACKER` | Disable DHT/PeX/LSD (true/false) | false |
| `GLUETUN_HOST` | Gluetun control server hostname | localhost |
| `GLUETUN_PORT` | Gluetun control server port | 8000 |
| `GLUETUN_AUTH_TYPE` | Auth type: none, basic, or apikey | none |
| `GLUETUN_API_KEY` | Gluetun API key | null |
| `DAYS` | Days between port renewal | 6 |
| `TIME` | Time of day to run (HH:MM) | 02:00 |
| `ONESHOT` | Run once and exit (true/false) | false |
| `WS_DEBUG` | Enable debug logging (true/false) | false |
| `REQUEST_TIMEOUT` | HTTP timeout in seconds | 5 |

### Gluetun Authentication Note
By default, this project uses `GLUETUN_AUTH_TYPE=none`. 
Because `ws-ephemeral` is designed to be deployed directly on the same Docker network as Gluetun (specifically sharing its network stack natively via `network_mode: service:gluetun`), the Gluetun control API is entirely secluded from the outside world. Since no external traffic can reach the control server, configuring API keys or Basic Auth introduces unnecessary friction for a purely internal, sealed container-to-container pipeline.

## Docker Compose Example

```yaml
version: "3.8"

services:
  gluetun:
    image: qmcgaw/gluetun:latest
    container_name: gluetun
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun:/dev/net/tun
    environment:
      # Windscribe VPN credentials (for OpenVPN connection)
      # These are DIFFERENT from the website credentials used for cookies
      - VPN_SERVICE_PROVIDER=windscribe
      - VPN_TYPE=openvpn
      - OPENVPN_USER=${OPENVPN_USER}
      - OPENVPN_PASSWORD=${OPENVPN_PASSWORD}
      - SERVER_CITIES=${SERVER_CITIES} # Server city for VPN
      - FIREWALL_VPN_INPUT_PORTS=${TORRENTING_PORT:-10412} # Port for torrent traffic
      - HTTP_CONTROL_SERVER_AUTH_DEFAULT_ROLE={"auth":"none"}
      - DOT=off
    ports:
      - "8080:8080" # Expose qbit
    volumes:
      - gluetun_data:/gluetun
      - ./gluetun/auth:/gluetun/auth
    restart: unless-stopped

  qbittorrent:
    image: lscr.io/linuxserver/qbittorrent:latest
    container_name: qbittorrent
    # Runs inside gluetun network stack (all traffic goes through VPN)
    network_mode: service:gluetun
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Budapest
      - WEBUI_PORT=8080 # qBittorrent web UI port
      - TORRENTING_PORT=${TORRENTING_PORT:-10412} # Port for incoming torrent connections
    volumes:
      - qbittorrent_config:/config
      - /mnt/downloads:/downloads
    depends_on:
      - gluetun
    restart: unless-stopped

  ws-ephemeral:
    container_name: ws-ephemeral
    build: .
    image: ws-ephemeral
    network_mode: service:gluetun
    environment:
      # === Windscribe session cookie ===
      - WS_SESSION_COOKIE=${WS_SESSION_COOKIE}
      - WS_DEBUG=False
      - TZ=${TZ:-UTC}

      # === qBittorrent settings ===
      - QBIT_HOST=localhost
      - QBIT_PORT=8080
      - QBIT_USERNAME=${QBIT_USERNAME} # qBittorrent web UI username
      - QBIT_PASSWORD=${QBIT_PASSWORD} # qBittorrent web UI password
      - QBIT_PRIVATE_TRACKER=true # Disable DHT/PeX/LSD for private trackers

      # === Gluetun settings ===
      - GLUETUN_HOST=localhost # Gluetun container hostname
      - GLUETUN_PORT=8000 # Gluetun control server port
      - GLUETUN_AUTH_TYPE=none # Auth type: none, basic, or apikey

      # === Schedule settings ===
      - DAYS=6 # Run every N days
      - TIME=02:00 # Time of day to run (HH:MM)
      - ONESHOT=false # Set to true to run once and exit
      - REQUEST_TIMEOUT=10 # HTTP request timeout in seconds
    depends_on:
      - gluetun
      - qbittorrent
    restart: unless-stopped

# Named volumes for persistent data
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

We use Astral's `uv` for blazingly fast dependency management.

```bash
# Install dependencies cleanly
uv sync

# Configure
cp .env.example .env
# Edit .env with your credentials

# Run the application (reads the ONESHOT variable from your .env to determine daemon or run-once mode)
uv run python src/app.py
```

## License

This project is a heavily modernized fork of [dhruvinsh/ws-ephemeral](https://github.com/dhruvinsh/ws-ephemeral). 
It remains licensed under the **GNU General Public License v3.0 (GPL-3.0)** in accordance with the original project's terms. 

See [LICENSE.md](LICENSE.md) for full details.