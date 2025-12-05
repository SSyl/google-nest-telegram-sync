# Google Nest Camera Telegram Sync

This is a fork of [TamirMa/google-nest-telegram-sync](https://github.com/TamirMa/google-nest-telegram-sync) with modernized features and Docker support.

## Credits

Original project by [Tamir Mayer](https://github.com/TamirMa). Read their story behind the project [here](https://medium.com/@tamirmayer/google-nest-camera-internal-api-fdf9dc3ce167).

Additional thanks to:
- [glocaltokens](https://github.com/leikoilja/glocaltokens) - Google authentication
- [ha-google-home_get-token](https://hub.docker.com/r/breph/ha-google-home_get-token) - Token extraction tool

## Overview

Automatically sync video clips from your Google Nest cameras to a Telegram channel with **full event type detection** (person, package, animal, vehicle, motion, sound). Uses Google's unofficial APIs to capture all events without requiring a Nest Aware subscription or Smart Device Management API.

**For personal use only. Use at your own risk.**

### Why This Approach?

Google's official Smart Device Management (SDM) API only exposes person/motion/sound events and **completely misses package, animal, and vehicle detection**. This project uses Google's internal Home API (the same API their website uses) to get complete event information including precise event types.

**Benefits:**
- Full event type detection with accurate labels
- Multiple event types combined automatically (e.g., "Package seen · Person")
- No Nest Aware subscription required
- Works with the same APIs Google's own website uses

**Example captions:**
- "Package seen · Person - Front Door [07:23:54 PM 12/04/2025]"
- "Person Seen - Front Door [03:50:39 PM 12/04/2025]"
- "Motion Detected - Back Yard [11:15:32 AM 12/04/2025]"

## Key Improvements Over Original

- **Full Event Type Detection**: Uses Google Home API to show event types (person, package, animal, vehicle, motion, sound) in captions
- **Automatic Event Combining**: Multiple concurrent events shown together (e.g., "Package seen · Person")
- **Precise Timestamp Matching**: Uses Google's internal API timestamps for perfect event-to-video alignment
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
      - sent-events:/app
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
  -v nest-events:/app \
  --restart unless-stopped \
  ssyl/nest-telegram-sync:latest
```

**Or build locally:**
```bash
docker build -t nest-telegram-sync .
docker run -d \
  --name nest-telegram-sync \
  --env-file .env \
  -v nest-events:/app \
  --restart unless-stopped \
  nest-telegram-sync
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_MASTER_TOKEN` | ✅ Yes | - | Your Google master token |
| `GOOGLE_USERNAME` | ✅ Yes | - | Your Google account email |
| `TELEGRAM_BOT_TOKEN` | ✅ Yes | - | Your Telegram bot token |
| `TELEGRAM_CHANNEL_ID` | ✅ Yes | - | Your Telegram channel ID |
| `REFRESH_INTERVAL_MINUTES` | No | `2` | How often to check for new videos (in minutes) |
| `TIMEZONE` | No | Auto-detected | Timezone for timestamps (e.g., `US/Eastern`, `Europe/London`) |
| `TIME_FORMAT` | No | System locale | `24h`, `12h`, or custom strftime format |
| `DRY_RUN` | No | `false` | Download videos but don't send to Telegram (testing) |
| `LOG_LEVEL` | No | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `VERBOSE` | No | `false` | Extra detailed logging (XML dumps, API responses) |
| `FORCE_RESEND_ALL` | No | `false` | Ignore sent history (for testing) |

### Time Format Examples

- `TIME_FORMAT=24h` → `23:40:50 22/10/2025`
- `TIME_FORMAT=12h` → `11:40:50PM 10/22/2025`
- `TIME_FORMAT=%Y-%m-%d %H:%M:%S` → `2025-10-22 23:40:50`
- Not set → Uses system locale default

## How It Works

1. The script runs on a configurable schedule (default: every 2 minutes)
2. Fetches camera events from **Google Home API** (last 3 hours)
   - Gets event types (person, package, animal, vehicle, motion, sound)
   - Gets precise timestamps for each event
   - Automatically combines multiple concurrent events
3. Downloads video clips from **Nest API** using timestamps from Google Home
4. Sends videos to your Telegram channel with event type and timestamp
5. Tracks sent events in `sent_events.json` to prevent duplicates
6. Auto-cleans events older than 7 days from the tracking file

**Architecture Note:** This mirrors Google's own website architecture:
- Google Home API provides event metadata and types
- Nest API provides video file storage and delivery

## Requirements

- Python 3.9+
- Google Nest camera
- Telegram bot and channel

See `requirements.txt` for all Python dependencies.

## Troubleshooting

**No videos arriving?**
```bash
docker compose logs -f nest-sync
```
Look for:
- `Found X Camera Device(s)` - Confirms authentication works
- `Fetched X events from Google Home` - Shows events were found with types
- `Using Google Home API events` - Confirms primary path is working
- `Downloaded and sent: X` - Videos successfully sent

**Wrong timestamps?**
Set `TIMEZONE` explicitly in your `.env` file (e.g., `TIMEZONE=America/New_York`).

**Want to test without sending to Telegram?**
Set in `.env`:
```env
DRY_RUN=true
LOG_LEVEL=DEBUG
```

**Container keeps restarting?**
Ensure all 4 required environment variables are set in `.env`.

## License & Disclaimer

This project maintains the same license as the original. This is an unofficial tool for personal use - not affiliated with or endorsed by Google or Telegram.
