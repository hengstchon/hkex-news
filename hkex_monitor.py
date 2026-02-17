#!/usr/bin/env python3
"""
HKEX New Listings Monitor with Telegram Alerts
Monitors the HKEX News API for new IPO listings and sends Telegram notifications
"""

import json
import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Set, List, Dict, Any, Optional
import requests
from telegram import Bot
from telegram.constants import ParseMode

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("hkex_monitor.log")],
)
logger = logging.getLogger(__name__)

# File paths
CONFIG_FILE = Path("config.json")
STATE_FILE = Path("listings_state.json")


class HKEXMonitor:
    def __init__(self):
        self.config = self._load_config()
        self.bot = Bot(token=self.config["telegram_bot_token"])
        self.chat_id = self.config["telegram_chat_id"]
        self.poll_interval = self.config.get("poll_interval_seconds", 60)
        self.api_url = self.config.get(
            "api_url",
            "https://www1.hkexnews.hk/ncms/json/eds/appactive_app_sehk_c.json",
        )
        self.seen_ids: Set[int] = set()
        self._load_state()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json"""
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Validate required fields
            if config.get("telegram_bot_token") == "YOUR_BOT_TOKEN_HERE":
                raise ValueError("Please set your Telegram bot token in config.json")
            if config.get("telegram_chat_id") == "YOUR_CHAT_ID_HERE":
                raise ValueError("Please set your Telegram chat ID in config.json")

            return config
        except FileNotFoundError:
            logger.error(f"Config file not found: {CONFIG_FILE}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            raise

    def _load_state(self) -> None:
        """Load previously seen listing IDs from state file"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    self.seen_ids = set(state.get("seen_ids", []))
                    logger.info(f"Loaded {len(self.seen_ids)} previously seen listings")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Could not load state file: {e}")
                self.seen_ids = set()
        else:
            logger.info("No state file found, starting fresh")
            self.seen_ids = set()

    def _save_state(self) -> None:
        """Save current seen IDs to state file"""
        state = {
            "last_check": datetime.now().isoformat(),
            "seen_ids": list(self.seen_ids),
            "total_seen": len(self.seen_ids),
        }
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def fetch_listings(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch current listings from HKEX API"""
        try:
            # Add cache-busting timestamp
            timestamp = int(time.time() * 1000)
            url = f"{self.api_url}?_={timestamp}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json",
            }

            logger.info(f"Fetching listings from HKEX API...")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            listings = data.get("app", [])

            logger.info(f"Fetched {len(listings)} listings from API")
            return listings

        except requests.RequestException as e:
            logger.error(f"Failed to fetch listings: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response: {e}")
            return None

    def detect_new_listings(
        self, listings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect listings that haven't been seen before"""
        new_listings = []
        current_ids = set()

        for listing in listings:
            listing_id = listing.get("id")
            if listing_id:
                current_ids.add(listing_id)
                if listing_id not in self.seen_ids:
                    new_listings.append(listing)

        # Update seen IDs with all current listings
        self.seen_ids.update(current_ids)

        if new_listings:
            logger.info(f"Detected {len(new_listings)} new listings")
        else:
            logger.debug("No new listings detected")

        return new_listings

    def format_telegram_message(self, listing: Dict[str, Any]) -> str:
        """Format a listing into a Telegram message"""
        company_name = listing.get("a", "Unknown Company")
        listing_date = listing.get("d", "Unknown Date")
        status = listing.get("s", "Unknown")
        listing_id = listing.get("id", "N/A")
        posting_date = listing.get("postingDate", "Unknown")
        has_phip = listing.get("hasPhip", False)

        # Build document links
        doc_links = []
        links = listing.get("ls", [])

        for link in links:
            doc_date = link.get("d", "")
            # Use nS2 (多檔案) label if available, otherwise fall back to nS1 or nF
            doc_name = (
                link.get("nS2", "") or link.get("nS1", "") or link.get("nF", "Document")
            )
            # Prioritize u2 (多檔案 HTML link), fall back to u1 (全文檔案 PDF)
            doc_url = link.get("u2", "") or link.get("u1", "")

            if doc_url:
                # Build full URL
                if doc_url.startswith("http"):
                    full_url = doc_url
                else:
                    full_url = f"https://www1.hkexnews.hk/app/{doc_url}"

                doc_links.append(f"• [{doc_name}]({full_url})")

        # Format status
        status_text = {
            "A": "Active (Application Proof)",
            "I": "Inactive",
            "W": "Withdrawn",
        }.get(status, status)

        # Build message
        message = f"""🚨 **New HKEX Listing Detected!**

**Company:** {company_name}
**Listing Date:** {listing_date}
**Status:** {status_text}
**ID:** `{listing_id}`
**Posted:** {posting_date}
**Has PHIP:** {"Yes" if has_phip else "No"}

📄 **Documents:**
"""

        if doc_links:
            message += "\n".join(doc_links)
        else:
            message += "• No documents available"

        message += f"""

[View All Listings](https://www1.hkexnews.hk/app/appindex.html?lang=zh)

_Detected at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}_"""

        return message

    async def send_telegram_alerts(self, new_listings: List[Dict[str, Any]]) -> None:
        """Send Telegram alerts for new listings"""
        for listing in new_listings:
            try:
                message = self.format_telegram_message(listing)
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=False,
                )
                logger.info(f"Sent alert for listing ID {listing.get('id')}")

                # Small delay to avoid hitting rate limits
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(
                    f"Failed to send Telegram message for listing {listing.get('id')}: {e}"
                )

    async def run_once(self) -> None:
        """Run a single check cycle"""
        listings = self.fetch_listings()

        if listings is None:
            logger.error("Failed to fetch listings, skipping this cycle")
            return

        new_listings = self.detect_new_listings(listings)

        if new_listings:
            await self.send_telegram_alerts(new_listings)
        else:
            logger.info("No new listings to report")

        # Always save state after each check
        self._save_state()

    async def run_continuous(self) -> None:
        """Run continuous monitoring loop"""
        logger.info(f"Starting continuous monitoring (interval: {self.poll_interval}s)")
        logger.info(f"Monitoring {len(self.seen_ids)} previously seen listings")

        try:
            while True:
                await self.run_once()
                logger.info(f"Sleeping for {self.poll_interval} seconds...")
                await asyncio.sleep(self.poll_interval)

        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error in monitoring loop: {e}")
            raise
        finally:
            self._save_state()
            logger.info(f"Final state saved. Total seen: {len(self.seen_ids)} listings")


async def main():
    """Main entry point"""
    print("=" * 60)
    print("HKEX New Listings Monitor")
    print("=" * 60)

    try:
        monitor = HKEXMonitor()
        await monitor.run_continuous()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Error: {e}")
        print("\nPlease check:")
        print("1. config.json exists and has valid Telegram credentials")
        print("2. You have internet connection")
        print("3. The HKEX API is accessible")
        raise


if __name__ == "__main__":
    asyncio.run(main())
