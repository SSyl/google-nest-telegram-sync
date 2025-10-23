# Google Nest Camera Telegram Sync

This is a fork of [TamirMa/google-nest-telegram-sync](https://github.com/TamirMa/google-nest-telegram-sync) with modernized features and Docker support.

## Credits

Original project by [Tamir Mayer](https://github.com/TamirMa). Read their story beind the project [here](https://medium.com/@tamirmayer/google-nest-camera-internal-api-fdf9dc3ce167).

Additional thanks to:
- [glocaltokens](https://github.com/leikoilja/glocaltokens) - Google authentication
- [ha-google-home_get-token](https://hub.docker.com/r/breph/ha-google-home_get-token) - Token extraction tool

## Overview

Automatically sync video clips from your Google Nest cameras to a Telegram channel. Runs on a schedule, tracks sent videos to avoid duplicates, and supports flexible timezone and formatting options.

**For personal use only. Use at your own risk.**

## Key Improvements Over Original

- **Configurable Timezone**: Auto-detects system timezone or set via `TIMEZONE` environment variable
- **Flexible Time Formatting**: Choose 24h/12h format or provide custom strftime patterns
- **Persistent Event Tracking**: Saves to `sent_events.json` to prevent duplicate sends across restarts
- **Modern Dependencies**: Updated to latest package versions, Python 3.13+ compatible
- **Docker Support**: Includes Dockerfile and docker-compose.yaml for containerized deployment
- **Auto-cleanup**: Automatically removes event records older than 7 days

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

### Option 2: Docker

1. Build and run with Docker:
```bash
docker build -t nest-telegram-sync .
docker run -d \
  --name nest-telegram-sync \
  --env-file .env \
  -v $(pwd)/sent_events.json:/app/sent_events.json \
  --restart unless-stopped \
  nest-telegram-sync
```

2. Or use Docker Compose:
```bash
docker compose up -d
```

View logs:
```bash
docker compose logs -f nest-sync
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REFRESH_INTERVAL_MINUTES` | No | `2` | How often to check for new videos (in minutes) |
| `GOOGLE_USERNAME` | ✅ Yes | - | Your Google account email |
| `GOOGLE_MASTER_TOKEN` | ✅ Yes | - | Your Google master token |
| `TELEGRAM_BOT_TOKEN` | ✅ Yes | - | Your Telegram bot token |
| `TELEGRAM_CHANNEL_ID` | ✅ Yes | - | Your Telegram channel ID |
| `TIMEZONE` | No | Auto-detected | Timezone for timestamps (e.g., `US/Eastern`, `Europe/London`) |
| `TIME_FORMAT` | No | System locale | `24h`, `12h`, or custom strftime format |
| `FORCE_RESEND_ALL` | No | `false` | Set to `true` to ignore sent history (for testing) |

### Time Format Examples

- `TIME_FORMAT=24h` → `23:40:50 22/10/2025`
- `TIME_FORMAT=12h` → `11:40:50PM 10/22/2025`
- `TIME_FORMAT=%Y-%m-%d %H:%M:%S` → `2025-10-22 23:40:50`
- Not set → Uses system locale default

## How It Works

1. The script runs on a configurable schedule (default: every 2 minutes)
2. Checks for new camera events in the last 3 hours (Google's retention limit)
3. Downloads any new video clips
4. Sends them to your Telegram channel with timestamp
5. Tracks sent events in `sent_events.json` to prevent duplicates
6. Auto-cleans events older than 7 days from the tracking file

## Requirements

- Python 3.9+
- Google Nest camera
- Telegram bot and channel

See `requirements.txt` for all Python dependencies.

## Troubleshooting

**Wrong timestamps?**
Set `TIMEZONE` explicitly in your `.env` file (e.g., `TIMEZONE=America/New_York`).

## License & Disclaimer

This project maintains the same license as the original. This is an unofficial tool for personal use - not affiliated with or endorsed by Google or Telegram.
