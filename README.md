# HKEX New Listings Monitor

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automatically monitors the Hong Kong Stock Exchange (HKEX) for new IPO listings and sends Telegram alerts when new Application Proofs are submitted.

## Features

- 🔍 **Real-time Monitoring**: Polls HKEX API every 60 seconds (configurable)
- 📱 **Telegram Alerts**: Instant notifications for new listings
- 💾 **State Persistence**: Tracks seen listings to avoid duplicates
- 🔗 **Smart Links**: Links to multi-file HTML documents instead of PDFs
- 🐍 **Modern Python**: Uses `uv` for fast dependency management

## Installation

### Prerequisites

- Python 3.8 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/hkex-news.git
   cd hkex-news
   ```

2. **Create configuration file**
   ```bash
   cp config.json.example config.json
   ```

3. **Edit `config.json` with your Telegram credentials:**
   ```json
   {
     "telegram_bot_token": "123456789:ABCdefGHIjklMNOpqrSTUvwxyz",
     "telegram_chat_id": "-1001234567890",
     "poll_interval_seconds": 60
   }
   ```

4. **Run the monitor**
   ```bash
   ./run.sh
   ```

   Or manually:
   ```bash
   uv venv
   uv pip install -r requirements.txt
   uv run python hkex_monitor.py
   ```

## Configuration

### Getting Telegram Bot Token

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the bot token provided

### Getting Chat ID

**For Channels:**
1. Add your bot to the channel as an administrator
2. Send a message in the channel
3. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Look for `"chat":{"id":-1001234567890` in the response

**For Groups:**
- Same as channels, or use [@userinfobot](https://t.me/userinfobot)

### Customizing Polling Interval

Edit `config.json`:
```json
{
  "poll_interval_seconds": 300  // Check every 5 minutes
}
```

## How It Works

1. **Fetch**: Retrieves current listings from HKEX API
2. **Compare**: Checks against previously seen listing IDs
3. **Detect**: Identifies new listings by unique ID
4. **Alert**: Sends formatted Telegram message with:
   - Company name (Chinese & English when available)
   - Listing date
   - Status (Active/Inactive/Withdrawn)
   - Links to documents (multi-file HTML pages)
   - Document types (整體協調人公告, 申請版本, etc.)

## Example Alert

```
🚨 New HKEX Listing Detected!

Company: 再惠有限公司
Listing Date: 13/02/2026
Status: Active (Application Proof)
ID: 108171
Posted: Feb 13, 2026
Has PHIP: No

📄 Documents:
• 多檔案: https://www1.hkexnews.hk/app/sehk/2026/108171/2026013002029_c.htm
• 整體協調人公告－委任: https://www1.hkexnews.hk/app/sehk/2026/...

View All Listings

_Detected at: 2026-02-15 14:30:00_
```

## Project Structure

```
.
├── hkex_monitor.py       # Main monitoring script
├── run.sh               # Setup and run script
├── requirements.txt     # Python dependencies
├── config.json.example  # Configuration template
├── .gitignore          # Git ignore rules
├── LICENSE             # MIT License
└── README.md           # This file
```

**Generated files** (not committed):
- `config.json` - Your private configuration
- `listings_state.json` - Tracks seen listings
- `hkex_monitor.log` - Application logs

## API Details

The script uses HKEX's internal JSON API:
- **Endpoint**: `https://www1.hkexnews.hk/ncms/json/eds/appactive_app_sehk_c.json`
- **Method**: GET
- **Returns**: JSON with all active Main Board listings

### Response Structure

```json
{
  "genDate": "1771106410001",
  "uDate": "13/02/2026",
  "app": [
    {
      "id": 108171,
      "d": "13/02/2026",
      "a": "再惠有限公司",
      "s": "A",
      "ls": [
        {
          "d": "13/02/2026",
          "nS1": "整體協調人公告－委任",
          "nS2": "多檔案",
          "u1": "sehk/2026/108171/documents/...",
          "u2": "sehk/2026/108171/...htm"
        }
      ],
      "hasPhip": false,
      "postingDate": "Feb 13, 2026"
    }
  ]
}
```

## Running as a Service

### Using systemd (Linux)

Create `/etc/systemd/system/hkex-monitor.service`:

```ini
[Unit]
Description=HKEX New Listings Monitor
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/hkex-news
ExecStart=/path/to/uv run python hkex_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable hkex-monitor
sudo systemctl start hkex-monitor
sudo systemctl status hkex-monitor
```

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY hkex_monitor.py .
COPY config.json .

CMD ["python", "hkex_monitor.py"]
```

## Troubleshooting

### No alerts on first run

**Expected behavior**: The script saves all current listings to state without alerting. Only NEW listings after the first run trigger alerts.

### "Config file not found" error

Make sure you've created `config.json` from the example:
```bash
cp config.json.example config.json
# Then edit with your credentials
```

### Telegram messages not sending

1. Verify bot token is correct
2. Ensure bot is added to channel/group
3. Check chat ID format (should include `-` for channels)
4. Test manually: `curl "https://api.telegram.org/bot<TOKEN>/getMe"`

### API fetch failures

The HKEX API may occasionally timeout. The script will retry on the next poll cycle.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for informational purposes only. Not affiliated with HKEX. Always verify listing information on the official HKEX website.

## Acknowledgments

- HKEX for providing public listing data
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) library
