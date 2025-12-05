# Google Nest Camera to Telegram Sync

Syncs Google Nest camera videos to Telegram with event types (person, package, animal, vehicle, motion, sound).

**For personal or educational use only.**

## Quick Start

### 1. Get Google Master Token

```bash
docker run --rm -it breph/ha-google-home_get-token
```

Tip: Use an app-specific password from https://myaccount.google.com/apppasswords

### 2. Create `.env` File

```env
# Required
GOOGLE_MASTER_TOKEN="aas_et/YOUR_TOKEN_HERE"
GOOGLE_USERNAME="youremail@gmail.com"
TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHANNEL_ID="-1001234567890"

# Optional
TIMEZONE=US/Central              # Auto-detected if not set
TIME_FORMAT=12h                  # Options: 24h, 12h, or custom strftime
REFRESH_INTERVAL_MINUTES=2       # How often to check for new events
DRY_RUN=false                    # Set true to test without sending
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR
```

### 3. Run with Docker Compose

**`docker-compose.yaml`:**
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
      - FORCE_RESEND_ALL=${FORCE_RESEND_ALL:-false}
      - DRY_RUN=${DRY_RUN:-false}
      - REFRESH_INTERVAL_MINUTES=${REFRESH_INTERVAL_MINUTES:-2}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - VERBOSE=${VERBOSE:-false}
    volumes:
      - nest-events:/app/nest-events
    env_file:
      - .env

volumes:
  nest-events:
```

```bash
docker compose up -d
docker compose logs -f nest-sync
```

### 4. Or Run Directly

```bash
docker run -d \
  --name nest-telegram-sync \
  --env-file .env \
  -v nest-events:/app/nest-events \
  --restart unless-stopped \
  ssyl/nest-telegram-sync:latest

# View logs
docker logs -f nest-telegram-sync
```

## Features

- Event type detection (person, package, animal, vehicle, motion, sound)
- Configurable polling interval
- Timezone and time format support
- Deduplication tracking
- Docker support

## Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_MASTER_TOKEN` | ✅ | - | OAuth master token from Google |
| `GOOGLE_USERNAME` | ✅ | - | Your Google account email |
| `TELEGRAM_BOT_TOKEN` | ✅ | - | Bot token from @BotFather |
| `TELEGRAM_CHANNEL_ID` | ✅ | - | Target channel ID (negative number) |
| `TIMEZONE` | ❌ | Auto-detected | IANA timezone (e.g., `US/Eastern`, `Europe/London`) |
| `TIME_FORMAT` | ❌ | System locale | `24h`, `12h`, or custom strftime format |
| `REFRESH_INTERVAL_MINUTES` | ❌ | `2` | How often to poll for events (1-60 minutes) |
| `FORCE_RESEND_ALL` | ❌ | `false` | Ignore sent history (for testing) |
| `DRY_RUN` | ❌ | `false` | Download videos but don't send to Telegram |
| `LOG_LEVEL` | ❌ | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `VERBOSE` | ❌ | `false` | Extra detailed logging (XML dumps, API responses) |

## How It Works

1. Polls every 2 minutes (configurable)
2. Fetches events from Google Home API (last 3 hours)
3. Downloads video clips from Nest API
4. Sends to Telegram with event type and timestamp
5. Tracks sent events to prevent duplicates

## Getting Credentials

**Telegram Bot Token:** Message [@BotFather](https://t.me/BotFather), send `/newbot`

**Telegram Channel ID:** Forward a channel message to [@userinfobot](https://t.me/userinfobot)

**Google Master Token:**
```bash
docker run --rm -it breph/ha-google-home_get-token
```

Tip: Use an app-specific password: https://myaccount.google.com/apppasswords

## Troubleshooting

Check logs: `docker compose logs -f nest-sync`

- **No videos?** Check that all 4 required env vars are set
- **Wrong timezone?** Set `TIMEZONE` in `.env`
- **Testing?** Set `DRY_RUN=true` and `LOG_LEVEL=DEBUG`

## Documentation

https://github.com/SSyl/google-nest-telegram-sync

## Credits

Fork of [TamirMa/google-nest-telegram-sync](https://github.com/TamirMa/google-nest-telegram-sync)

Thanks to:
- [glocaltokens](https://github.com/leikoilja/glocaltokens)
- [ha-google-home_get-token](https://hub.docker.com/r/breph/ha-google-home_get-token)

## License

MIT License. For personal or educational use only.

Unofficial tool, not affiliated with Google or Telegram. Use at your own risk.