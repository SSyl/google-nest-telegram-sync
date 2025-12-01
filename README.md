# Google Nest Camera → Telegram Sync

Automatically receive real-time video clips from your Google Nest cameras in a Telegram channel whenever motion, people, packages, or other events are detected.

**For personal use only. Use at your own risk.**

## Features

- 🔔 **Real-time notifications** via Google Cloud Pub/Sub (no polling!)
- 📦🧍🦖 **Emoji support** for event types (Package, Person, Animal, etc.)
- 🕐 **Smart deduplication** prevents duplicate videos
- 🌍 **Timezone support** with flexible time formatting
- 🐳 **Docker-first** deployment with volume persistence
- ⚡ **Fast delivery** - Videos sent ~30 seconds after event occurs
- 🎯 **Multiple event detection** - Shows all detected events in one message

## Credits

Fork of [TamirMa/google-nest-telegram-sync](https://github.com/TamirMa/google-nest-telegram-sync) with major architectural updates.

Additional thanks to:
- [glocaltokens](https://github.com/leikoilja/glocaltokens) - Google authentication
- [ha-google-home_get-token](https://hub.docker.com/r/breph/ha-google-home_get-token) - Token extraction tool

---

## Prerequisites

Before you begin, you'll need:
- A Google Nest camera
- A Google account with access to the camera
- $5 USD for one-time Google Device Access fee
- A Telegram account
- Docker (recommended) or Python 3.9+

---

## Setup Guide

### Part 1: Google Smart Device Management API Setup

#### Step 1: Pay the $5 Device Access Fee

1. Go to [Google Device Access Console](https://console.nest.google.com/device-access/)
2. Click **"Go to the Device Access Console"**
3. Accept the Terms of Service
4. Pay the **$5 USD one-time fee** (required by Google)

#### Step 2: Create a Device Access Project

1. In the Device Access Console, click **"Create project"**
2. Enter a project name (e.g., "Nest Telegram Sync")
3. Click **"Next"** and then **"Create project"**
4. **Save your Project ID** - you'll need this later

#### Step 3: Enable the Smart Device Management API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one (can be different from Device Access project)
3. Go to [**APIs & Services** → **Library**](https://console.cloud.google.com/apis/library)
4. Search for **"Smart Device Management API"** or [click here](https://console.cloud.google.com/apis/library/smartdevicemanagement.googleapis.com)
5. Click **"Enable"**

#### Step 4: Create OAuth Credentials

1. In Google Cloud Console, go to [**APIs & Services** → **Credentials**](https://console.cloud.google.com/apis/credentials)
2. Click **"Create Credentials"** → **"OAuth client ID"**
3. If prompted, configure the [OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent):
   - User Type: **External**
   - App name: Any name (e.g., "Nest Sync")
   - User support email: Your email
   - Developer contact: Your email
   - Add yourself as a test user under **Test users**
4. Back in [Credentials](https://console.cloud.google.com/apis/credentials), create OAuth client ID:
   - Application type: **Web application**
   - Name: Any name
   - Authorized redirect URIs: `https://www.google.com`
5. **Download the JSON file** and save it temporarily

#### Step 5: Get Refresh Token

1. Run this helper script to get your refresh token:
   ```bash
   python get_sdm_refresh_token.py
   ```
   (This script is included in the repo - it will guide you through OAuth flow)

2. Or manually:
   - Visit the OAuth URL the script provides
   - Sign in with your Google account
   - Copy the authorization code from the URL
   - Exchange it for a refresh token

3. **Save the refresh token** for later

#### Step 6: Create Service Account

1. In Google Cloud Console, go to [**IAM & Admin** → **Service Accounts**](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Click **"Create Service Account"**
   - Name: "nest-pubsub-listener" (or any name)
   - Click **"Create and Continue"**
3. Grant role: **Pub/Sub Subscriber**
4. Click **"Done"**
5. Click on the service account you just created
6. Go to **"Keys"** tab
7. Click **"Add Key"** → **"Create new key"**
8. Choose **JSON** format
9. **Download and save as `service-account.json`** in your project directory

#### Step 7: Set Up Pub/Sub Topic

1. In Google Cloud Console, go to [**Pub/Sub** → **Topics**](https://console.cloud.google.com/cloudpubsub/topic/list)
2. Click **"Create Topic"**
   - Topic ID: `nest-events` (or any name)
   - Leave other settings as default
   - Click **"Create"**
3. **Copy the full topic name** (format: `projects/YOUR_PROJECT_ID/topics/nest-events`)

#### Step 8: Link Device Access Project to Pub/Sub

1. Go back to [Device Access Console](https://console.nest.google.com/device-access/)
2. Select your project
3. Click **"Enable Pub/Sub"** or go to **Settings**
4. Enter your **Pub/Sub topic name** from Step 7
5. Click **"Enable"**

### Part 2: Telegram Bot Setup

#### Step 9: Create Telegram Bot

1. Open Telegram and search for **@BotFather** or use these links:
   - **Web/Desktop**: [https://t.me/BotFather](https://t.me/BotFather)
   - **Direct link**: [Open @BotFather in Telegram](tg://resolve?domain=BotFather)
2. Click **"Start"** or **"Restart"** if you've used it before
3. Send the command: `/newbot`
4. Choose a **display name** for your bot (e.g., "My Nest Camera")
5. Choose a **username** (must end in 'bot', e.g., `mynestcamera_bot`)
6. **Copy and save the bot token** (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)
   - ⚠️ Keep this secret! Anyone with this token can control your bot

#### Step 10: Create Telegram Channel

1. In Telegram, create a new channel:
   - **Mobile**: Tap the pencil/compose icon → **"New Channel"**
   - **Desktop**: Click the menu → **"New Channel"**
   - **Web**: Go to [https://web.telegram.org](https://web.telegram.org) → Click "+" → **"New Channel"**
2. Configure the channel:
   - Name: Any name (e.g., "Nest Camera Events")
   - Description: Optional
   - Channel type: Choose **"Private"** (recommended)
3. Add your bot as an administrator:
   - Open your channel
   - Click the channel name at the top → **"Administrators"**
   - Click **"Add Administrator"**
   - Search for your bot's username (e.g., `@mynestcamera_bot`)
   - Select your bot
   - Grant at least **"Post Messages"** permission
   - Click **"Save"** or **"Done"**

#### Step 11: Get Channel ID

**Method 1: Using @userinfobot (Easiest)**

1. Send any message to your channel (e.g., "test")
2. Forward that message to **@userinfobot**:
   - **Web/Desktop**: [https://t.me/userinfobot](https://t.me/userinfobot)
   - **Direct link**: [Open @userinfobot in Telegram](tg://resolve?domain=userinfobot)
3. Click **"Start"** if prompted
4. The bot will immediately reply with your channel ID (format: `-1001234567890`)
5. **Copy and save this channel ID**

**Method 2: Using Telegram Web (Alternative)**

1. Open [https://web.telegram.org](https://web.telegram.org) in your browser
2. Log in to your account
3. Open your channel from the left sidebar
4. Look at the URL in your browser's address bar:
   - URL format: `https://web.telegram.org/k/#-1001234567890`
   - Your channel ID is the number after `#` (including the minus sign)
   - Example: If URL shows `#-1001234567890`, your channel ID is `-1001234567890`
5. **Copy and save this channel ID**

### Part 3: Get Google Master Token

#### Step 12: Extract Master Token

**Important:** This uses an unofficial method to access video clips. Consider using a Google app-specific password or two-factor authentication for security.

1. Run the token extraction tool:
   ```bash
   docker run --rm -it breph/ha-google-home_get-token
   ```

2. Follow the prompts to log in with your Google account
3. **Save the master token** (starts with `aas_et/...`)

### Part 4: Configuration

#### Step 13: Create .env File

Create a `.env` file in your project directory with all the values you saved:

```env
# ===== Google Account (for unofficial API) =====
GOOGLE_MASTER_TOKEN=aas_et/YOUR_MASTER_TOKEN_HERE
GOOGLE_USERNAME=youremail@gmail.com

# ===== Telegram Configuration =====
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHANNEL_ID=-1001234567890

# ===== Google Smart Device Management API (Official) =====
SDM_PROJECT_ID=your-device-access-project-id
SDM_SERVICE_ACCOUNT_FILE=service-account.json
SDM_PUBSUB_TOPIC=projects/your-cloud-project-id/topics/nest-events

# ===== Display Settings (Optional) =====
TIMEZONE=US/Central                    # Auto-detected if not set
TIME_FORMAT=12h                        # Options: 24h, 12h, or custom strftime

# ===== Debug/Development Settings (Optional) =====
DRY_RUN=false                          # Set to true to test without sending to Telegram
FORCE_RESEND_ALL=false                 # Set to true to ignore sent history
LOG_LEVEL=INFO                         # DEBUG, INFO, WARNING, ERROR
```

#### Step 14: Place service-account.json

Make sure `service-account.json` (from Step 6) is in your project directory.

---

## Installation & Running

### Option 1: Docker (Recommended)

1. **Ensure files exist:**
   ```bash
   ls -la .env service-account.json
   # Both files must exist
   ```

2. **Build and run:**
   ```bash
   docker compose up -d
   ```

3. **View logs:**
   ```bash
   docker compose logs -f nest-sync
   ```

4. **Test the setup:**
   - Trigger an event with your camera (walk in front of it)
   - Wait ~30 seconds
   - Check your Telegram channel for the video

### Option 2: Standard Python

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run:**
   ```bash
   python3 main.py
   ```

---

## How It Works

1. **Real-time events**: Google sends Pub/Sub notifications when camera detects events
2. **Smart filtering**: Only processes events with 'clippreview' (video ready indicator)
3. **Deduplication**: Tracks event IDs to prevent duplicate messages
4. **30-second wait**: Waits for video to be fully available
5. **Video download**: Fetches clip via unofficial Nest API (~1 minute duration)
6. **Telegram upload**: Sends video with emoji-rich caption

**Example notification:**
```
📦🧍 Package, Person Detected - Front Door [11:40:50 PM 12/01/2025]
```

## Supported Event Types

| Emoji | Event Type | Priority |
|-------|------------|----------|
| 🔔 | Doorbell | Highest |
| 📦 | Package | ↓ |
| 🧍 | Person | ↓ |
| 🦖 | Animal | ↓ |
| 🚗 | Vehicle | ↓ |
| 👀 | Motion | ↓ |
| 🔊 | Sound | Lowest |

Multiple events detected simultaneously are shown in priority order.

---

## Configuration Reference

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_MASTER_TOKEN` | OAuth master token from unofficial API | `aas_et/AC7f8d...` |
| `GOOGLE_USERNAME` | Your Google account email | `user@gmail.com` |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | `123456:ABC-DEF...` |
| `TELEGRAM_CHANNEL_ID` | Channel ID (negative number) | `-1001234567890` |
| `SDM_PROJECT_ID` | Device Access project ID | `a1b2c3d4-...` |
| `SDM_SERVICE_ACCOUNT_FILE` | Path to service account JSON | `service-account.json` |
| `SDM_PUBSUB_TOPIC` | Full Pub/Sub topic name | `projects/.../topics/nest-events` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TIMEZONE` | Auto-detected | IANA timezone (e.g., `US/Eastern`, `Europe/London`) |
| `TIME_FORMAT` | System locale | `24h`, `12h`, or custom strftime format |
| `DRY_RUN` | `false` | Skip Telegram upload (testing mode) |
| `FORCE_RESEND_ALL` | `false` | Ignore sent history (testing mode) |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Time Format Examples

- `TIME_FORMAT=24h` → `23:40:50 22/10/2025`
- `TIME_FORMAT=12h` → `11:40:50 PM 10/22/2025`
- `TIME_FORMAT=%Y-%m-%d %H:%M:%S` → `2025-10-22 23:40:50`

---

## Troubleshooting

### No events arriving

1. **Check Pub/Sub connection:**
   ```bash
   docker compose logs -f nest-sync | grep "Pub/Sub"
   ```
   Should see "Starting Pub/Sub listener..." and "Waiting for real-time events..."

2. **Verify Device Access project:**
   - Go to [Device Access Console](https://console.nest.google.com/device-access/)
   - Ensure Pub/Sub is enabled
   - Check topic name matches your `.env`

3. **Test with an event:**
   - Trigger your camera (walk in front of it)
   - Check logs for "Event received:"
   - If nothing appears, check SDM API credentials

### "Device not found" errors

**Symptom:** Logs show "Device '...' not found in configured cameras"

**Fix:** Device names from SDM API vs unofficial API may differ. Check logs for:
```
Available device names: ['Front Door']
```
The app uses partial name matching, but if names are completely different, you may need to adjust device discovery.

### Duplicate videos sent

**Should be fixed** in current version. If still happening:
1. Check logs for "already processed, skipping" messages
2. Delete `sent_events.json` and restart
3. Ensure you're running latest code with clippreview filtering

### Wrong timezone

Set `TIMEZONE` explicitly in `.env`:
```env
TIMEZONE=America/New_York
```

Find your timezone: [IANA timezone list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

### Service account errors

**Symptom:** "Permission denied" or "service account" errors

**Fix:**
1. Ensure `service-account.json` exists in project directory
2. Verify it's a valid JSON file (not a directory)
3. Check service account has **Pub/Sub Subscriber** role

### Container keeps restarting

1. **Check logs:**
   ```bash
   docker compose logs nest-sync
   ```

2. **Common issues:**
   - Missing `.env` file
   - Missing `service-account.json`
   - Invalid credentials
   - Incorrect Pub/Sub topic name

---

## Docker Hub

Pre-built images available at: `ssyl/nest-telegram-sync:latest`

To use the pre-built image instead of building locally, change `docker-compose.yaml`:
```yaml
services:
  nest-sync:
    image: ssyl/nest-telegram-sync:latest  # Instead of: build: .
```

---

## API Usage Notes

This application uses a **hybrid approach**:

- **Official SDM API**: Real-time notifications via Pub/Sub (unlimited usage)
- **Unofficial Nest API**: Video downloads only (~10-20 calls/day)

The unofficial API is minimized to reduce potential Terms of Service concerns. Video downloading is the only functionality not available through the official SDM API.

---

## Requirements

- Python 3.9+ (or Docker)
- Google Nest camera
- Active Google Device Access subscription ($5 one-time fee)
- Telegram bot and channel
- Google Cloud project with SDM API enabled

---

## License

MIT License - Same as original project.

## Disclaimer

This is an unofficial tool for personal use. Not affiliated with or endorsed by Google or Telegram. The unofficial Nest API usage is not documented by Google and may stop working at any time. Use at your own risk.
