# Google Nest Camera to Telegram Sync

Automatically sync video clips from your Google Nest doorbell cameras to a Telegram channel. Polls for new events every 2 minutes, captures **ALL event types** (person, package, animal, vehicle, motion, sound), and prevents duplicate sends.

**For education or personal use only.**

## Quick Start

### 1. Get Your Google Master Token

**Recommended:** Create an app password at https://myaccount.google.com/apppasswords that's unique for this project.

```bash
docker run --rm -it breph/ha-google-home_get-token
```

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

### 3. Run with Docker Compose (Recommended)

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
      - sent-events:/app
    env_file:
      - .env

volumes:
  sent-events:
```

**Start:**
```bash
docker compose up -d
docker compose logs -f nest-sync
```

### 4. Or Run Directly with Docker

```bash
docker run -d \
  --name nest-telegram-sync \
  --env-file .env \
  -v nest-events:/app \
  --restart unless-stopped \
  ssyl/nest-telegram-sync:latest
```

**View logs:**
```bash
docker logs -f nest-telegram-sync
```

## Features

- **🔄 Captures ALL events** - Person, package, animal, vehicle, motion, sound (not limited like Google's official API)
- **⏰ Configurable polling** - Check for new videos every 1-60 minutes
- **🌍 Timezone support** - Auto-detects system timezone or configure manually
- **🕐 Flexible time formats** - 24h, 12h (with AM/PM), or custom strftime patterns
- **💾 Persistent tracking** - Saves sent event IDs to prevent duplicates across restarts
- **🧹 Auto-cleanup** - Removes event records older than 7 days
- **🐳 Docker-optimized** - Named volumes, auto-restart, real-time logs
- **🔒 Secure logging** - Automatically filters sensitive tokens from logs

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

1. **Polls every 2 minutes** (configurable) for camera events
2. **Queries last 3 hours** of events from Google's unofficial Nest API
3. **Downloads new video clips** (skips already-sent events via `sent_events.json`)
4. **Sends to Telegram** with timestamp caption: `Front Door [11:40:50 PM 12/03/2025]`
5. **Cleans up old records** automatically (keeps last 7 days)

**Note:** Event captions show device name and timestamp only. Event types (person/package/animal) are not labeled because Google's official API doesn't expose this information for package/animal/vehicle detection.

## 🔧 Getting Credentials

### Telegram Bot Token
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow prompts
3. Save the bot token

### Telegram Channel ID
1. Send a message to your channel
2. Forward it to [@userinfobot](https://t.me/userinfobot)
3. Copy the channel ID (format: `-1001234567890`)

### Google Master Token
```bash
docker run --rm -it breph/ha-google-home_get-token
```

**Security tip:** Use a Google app-specific password instead of your main account password.

## 🐛 Troubleshooting

**No videos arriving?**
```bash
docker compose logs -f nest-sync
```

Look for:
- `Found X Camera Device(s)` - Confirms authentication works
- `Received X camera events` - Shows events were found
- `Downloaded and sent: X` - Videos successfully sent

**Wrong timezone?**
Set explicitly in `.env`:
```env
TIMEZONE=America/New_York
```

**Want to test without sending to Telegram?**
```env
DRY_RUN=true
LOG_LEVEL=DEBUG
```

**Container keeps restarting?**
Check you have all 4 required environment variables set in `.env`

## Full Documentation

Complete setup guide, examples, and troubleshooting:
**https://github.com/SSyl/google-nest-telegram-sync**

## Why Not Use Google's Official API?

Google's Smart Device Management (SDM) API **only detects person/motion/sound events**. It completely misses package, animal, and vehicle detection. This project uses Google's unofficial Nest API to capture **ALL event types**, even though we can't determine which type each event is at the moment.

## Credits

Fork of [TamirMa/google-nest-telegram-sync](https://github.com/TamirMa/google-nest-telegram-sync) with polling restoration and modern Docker support.

Additional thanks:
- [glocaltokens](https://github.com/leikoilja/glocaltokens) - Google authentication
- [ha-google-home_get-token](https://hub.docker.com/r/breph/ha-google-home_get-token) - Token extraction tool

---

## License & Disclaimer

MIT License - **For personal use only.**

This is an unofficial tool not affiliated with or endorsed by Google or Telegram. Uses Google's undocumented Nest API which may stop working at any time. Use at your own risk.