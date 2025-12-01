# Google Nest Camera → Telegram Sync

Automatically receive **real-time** video clips from your Google Nest cameras in a Telegram channel with emoji-rich notifications whenever motion, people, packages, or other events are detected.

**📦🧍 Package, Person Detected - Front Door [11:40 PM]**

## ✨ Features

- 🔔 **Real-time notifications** via Google Cloud Pub/Sub (no polling!)
- 📦🧍🦖 **Emoji support** - Visual indicators for all event types
- ⚡ **Fast delivery** - Videos sent ~30 seconds after event
- 🎯 **Smart deduplication** - Never receive duplicate videos
- 🌍 **Timezone support** - Flexible time formatting
- 🐳 **Docker-optimized** - Volume persistence, auto-restart

## ⚠️ Important: Prerequisites

This requires **Google Smart Device Management API setup** ($5 one-time fee):

1. ✅ Google Device Access subscription ($5 USD one-time)
2. ✅ Google Cloud project with SDM API enabled
3. ✅ Service account with Pub/Sub access
4. ✅ Pub/Sub topic configured
5. ✅ Telegram bot and channel

**See [full setup guide](https://github.com/SSyl/google-nest-telegram-sync#setup-guide) for step-by-step instructions with direct links.**

## 🚀 Quick Start

### 1. Create Required Files

**`.env` file:**
```env
# Google Account (for unofficial API)
GOOGLE_MASTER_TOKEN=aas_et/YOUR_MASTER_TOKEN
GOOGLE_USERNAME=youremail@gmail.com

# Telegram Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHANNEL_ID=-1001234567890

# Google Smart Device Management API (Official)
SDM_PROJECT_ID=your-device-access-project-id
SDM_SERVICE_ACCOUNT_FILE=service-account.json
SDM_PUBSUB_TOPIC=projects/your-cloud-project/topics/nest-events

# Optional Settings
TIMEZONE=US/Central
TIME_FORMAT=12h
LOG_LEVEL=INFO
```

**`service-account.json`** (from Google Cloud Console)

Place this file in the same directory as your docker-compose.yaml.

### 2. Docker Compose (Recommended)

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
      - SDM_PROJECT_ID=${SDM_PROJECT_ID}
      - SDM_SERVICE_ACCOUNT_FILE=${SDM_SERVICE_ACCOUNT_FILE}
      - SDM_PUBSUB_TOPIC=${SDM_PUBSUB_TOPIC}
      - TIMEZONE=${TIMEZONE:-UTC}
      - TIME_FORMAT=${TIME_FORMAT:-12h}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}

    volumes:
      - sent-events:/app
      - ./service-account.json:/app/service-account.json:ro

    env_file:
      - .env

volumes:
  sent-events:
```

**Start the container:**
```bash
docker compose up -d
docker compose logs -f nest-sync
```

### 3. Docker Run (Alternative)

**Ensure `service-account.json` exists first:**
```bash
ls -la service-account.json
```

**Run container:**
```bash
docker run -d \
  --name nest-telegram-sync \
  --env-file .env \
  -v nest-events:/app \
  -v $(pwd)/service-account.json:/app/service-account.json:ro \
  --restart unless-stopped \
  ssyl/nest-telegram-sync:latest
```

**View logs:**
```bash
docker logs -f nest-telegram-sync
```

## 📋 Configuration Reference

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_MASTER_TOKEN` | OAuth master token from unofficial API |
| `GOOGLE_USERNAME` | Your Google account email |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHANNEL_ID` | Target channel ID (negative number) |
| `SDM_PROJECT_ID` | Device Access project ID |
| `SDM_SERVICE_ACCOUNT_FILE` | Path to service account JSON |
| `SDM_PUBSUB_TOPIC` | Full Pub/Sub topic name |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TIMEZONE` | Auto-detected | IANA timezone (e.g., `US/Eastern`) |
| `TIME_FORMAT` | System locale | `24h`, `12h`, or custom strftime |
| `DRY_RUN` | `false` | Skip Telegram upload (testing) |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## 🎯 Supported Event Types

| Emoji | Event Type | Priority |
|-------|------------|----------|
| 🔔 | Doorbell | Highest |
| 📦 | Package | ↓ |
| 🧍 | Person | ↓ |
| 🦖 | Animal | ↓ |
| 🚗 | Vehicle | ↓ |
| 👀 | Motion | ↓ |
| 🔊 | Sound | Lowest |

Multiple events are shown in priority order: **📦🧍 Package, Person Detected**

## 🔧 How It Works

1. **Google sends Pub/Sub notification** when camera detects an event
2. **App filters for 'clippreview'** (video ready indicator)
3. **Deduplicates using event ID** to prevent duplicates
4. **Waits 30 seconds** for video to be fully available
5. **Downloads clip** via unofficial Nest API (~1 minute)
6. **Sends to Telegram** with emoji-rich caption

## ⚙️ Getting Credentials

### Google Master Token
```bash
docker run --rm -it breph/ha-google-home_get-token
```
**Note:** Consider using a Google app-specific password.

### Telegram Bot Token
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow prompts
3. Save the token

### Telegram Channel ID
1. Send a message to your channel
2. Forward it to [@userinfobot](https://t.me/userinfobot)
3. Copy the channel ID (format: `-1001234567890`)

### Google Cloud Setup
See the [complete setup guide](https://github.com/SSyl/google-nest-telegram-sync#part-1-google-smart-device-management-api-setup) with direct links to all Google Cloud Console pages.

## 🐛 Troubleshooting

### No events arriving
```bash
docker compose logs -f nest-sync | grep "Pub/Sub"
```
Should see: "Starting Pub/Sub listener..." and "Waiting for real-time events..."

**Common issues:**
- Pub/Sub topic not linked to Device Access project
- Service account missing Pub/Sub Subscriber role
- Incorrect topic name in `.env`

### Container keeps restarting
```bash
docker compose logs nest-sync
```

**Common causes:**
- Missing `service-account.json` file
- Missing or invalid `.env` file
- Incorrect SDM API credentials

### Wrong timezone
Set explicitly in `.env`:
```env
TIMEZONE=America/New_York
```

## 📚 Full Documentation

**Complete setup guide with screenshots and troubleshooting:**
[https://github.com/SSyl/google-nest-telegram-sync](https://github.com/SSyl/google-nest-telegram-sync)

## 🙏 Credits

Fork of [TamirMa/google-nest-telegram-sync](https://github.com/TamirMa/google-nest-telegram-sync) with major architectural updates (real-time Pub/Sub, emoji support, smart deduplication).

Additional thanks:
- [glocaltokens](https://github.com/leikoilja/glocaltokens) - Google authentication
- [ha-google-home_get-token](https://hub.docker.com/r/breph/ha-google-home_get-token) - Token extraction

---

## ⚖️ License & Disclaimer

MIT License - For personal use only.

This is an unofficial tool not affiliated with or endorsed by Google or Telegram. The unofficial Nest API usage is not documented by Google and may stop working at any time. Use at your own risk.

**Requires Google Device Access ($5 one-time fee).**
