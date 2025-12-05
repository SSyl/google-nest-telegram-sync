# Google Nest Camera Telegram Sync

This is a fork of [TamirMa/google-nest-telegram-sync](https://github.com/TamirMa/google-nest-telegram-sync) with modernized features and Docker support.

## Credits

Original project by [Tamir Mayer](https://github.com/TamirMa). Read their story behind the project [here](https://medium.com/@tamirmayer/google-nest-camera-internal-api-fdf9dc3ce167).

Additional thanks to:
- [glocaltokens](https://github.com/leikoilja/glocaltokens) - Google authentication
- [ha-google-home_get-token](https://hub.docker.com/r/breph/ha-google-home_get-token) - Token extraction tool

## Overview

Syncs Google Nest camera videos to Telegram. Includes event types (person, package, animal, vehicle, motion, sound) in captions.

Example: `Package seen · Person - Front Door [12/04/2025 07:23:54 PM]`

**For personal or educational use only. Use at your own risk.**

## Changes From Original Fork

- Event type detection (person, package, animal, vehicle, motion, sound)
- Configurable timezone and time format
- Event deduplication with `sent_events.json`
- Docker support
- Updated dependencies (Python 3.13+)

## Installation

### Option 1: Standard Python Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Get a Google "Master Token" (consider using a Google One-Time Password):
```bash
docker run --rm -it breph/ha-google-home_get-token
```

3. Create a `.env` file:
```env
GOOGLE_MASTER_TOKEN="aas_..."
GOOGLE_USERNAME="youremailaddress@gmail.com"
TELEGRAM_BOT_TOKEN="token..."
TELEGRAM_CHANNEL_ID="-100..."

# Optional settings
TIMEZONE=US/Central              # Auto-detected if not specified
TIME_FORMAT=12h                  # Options: 24h, 12h, or custom strftime format
REFRESH_INTERVAL_MINUTES=2       # How often to check for new videos (in minutes)
FORCE_RESEND_ALL=false          # Set to true for testing/debugging
```

4. Run:
```bash
python3 main.py
```

### Option 2: Docker (Recommended)

**Use Docker Compose:**

Create `docker-compose.yaml`:
```yaml
services:
  nest-sync:
    image: ssyl/nest-telegram-sync:latest
    container_name: nest-telegram-sync
    restart: unless-stopped
    environment:
      - GOOGLE_MASTER_TOKEN=${GOOGLE_MASTER_TOKEN}
      - GOOGLE_USERNAME=${GOOGLE_USERNAME}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHANNEL_ID=${TELEGRAM_CHANNEL_ID}
      - TIMEZONE=${TIMEZONE:-UTC}
      - TIME_FORMAT=${TIME_FORMAT:-24h}
      - REFRESH_INTERVAL_MINUTES=${REFRESH_INTERVAL_MINUTES:-2}
      - FORCE_RESEND_ALL=${FORCE_RESEND_ALL:-false}
      - DRY_RUN=${DRY_RUN:-false}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - VERBOSE=${VERBOSE:-false}
    volumes:
      - sent-events:/app/data
    env_file:
      - .env

volumes:
  sent-events:
```

Run:
```bash
docker compose up -d
docker compose logs -f nest-sync
```

**Or use Docker Hub image directly:**
```bash
docker run -d \
  --name nest-telegram-sync \
  --env-file .env \
  -v nest-events:/app/data \
  --restart unless-stopped \
  ssyl/nest-telegram-sync:latest
```

**Or build locally:**
```bash
docker build -t nest-telegram-sync .
docker run -d \
  --name nest-telegram-sync \
  --env-file .env \
  -v nest-events:/app/data \
  --restart unless-stopped \
  nest-telegram-sync
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_MASTER_TOKEN` | ✅ | - | Google master token |
| `GOOGLE_USERNAME` | ✅ | - | Google account email |
| `TELEGRAM_BOT_TOKEN` | ✅ | - | Telegram bot token |
| `TELEGRAM_CHANNEL_ID` | ✅ | - | Telegram channel ID |
| `REFRESH_INTERVAL_MINUTES` | No | `2` | Poll interval (minutes) |
| `TIMEZONE` | No | Auto | Timezone (e.g., `US/Eastern`) |
| `TIME_FORMAT` | No | Locale | `24h`, `12h`, or strftime format |
| `DRY_RUN` | No | `false` | Skip sending to Telegram |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `VERBOSE` | No | `false` | Detailed logging |
| `FORCE_RESEND_ALL` | No | `false` | Ignore sent history |

Time format: `24h`, `12h`, or custom strftime (e.g., `%Y-%m-%d %H:%M:%S`)

## How It Works

1. Polls every 2 minutes (configurable)
2. Fetches events from Google Home API (last 3 hours)
3. Downloads video clips from Nest API
4. Sends to Telegram with event type and timestamp
5. Tracks sent events to prevent duplicates

## Requirements

- Python 3.9+
- Google Nest camera
- Telegram bot and channel

See `requirements.txt` for all Python dependencies.

## Troubleshooting

Check logs: `docker compose logs -f nest-sync`

- **No videos?** Check that all 4 required env vars are set
- **Wrong timezone?** Set `TIMEZONE` in `.env`
- **Testing?** Set `DRY_RUN=true` and `LOG_LEVEL=DEBUG`

## License

MIT License. For personal or educational use only.

Unofficial tool, not affiliated with Google or Telegram. Use at your own risk.
