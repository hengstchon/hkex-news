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
        self.listing_docs: Dict[int, Set[str]] = {}  # {listing_id: {doc_url}}
        self.docs_tracking_initialized: bool = (
            False  # Flag to track if docs tracking is ready
        )
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
        """Load previously seen listing IDs and documents from state file"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    self.seen_ids = set(state.get("seen_ids", []))
                    # Load documents per listing
                    docs_data = state.get("listing_docs", {})
                    self.listing_docs = {int(k): set(v) for k, v in docs_data.items()}
                    # Flag to check if document tracking was already initialized
                    self.docs_tracking_initialized = len(self.listing_docs) > 0
                    logger.info(
                        f"Loaded {len(self.seen_ids)} previously seen listings, "
                        f"{len(self.listing_docs)} with document tracking, "
                        f"tracking_initialized: {self.docs_tracking_initialized}"
                    )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Could not load state file: {e}")
                self.seen_ids = set()
                self.listing_docs = {}
                self.docs_tracking_initialized = False
        else:
            logger.info("No state file found, starting fresh")
            self.seen_ids = set()
            self.listing_docs = {}

    def _save_state(self) -> None:
        """Save current seen IDs and documents to state file"""
        state = {
            "last_check": datetime.now().isoformat(),
            "seen_ids": list(self.seen_ids),
            "total_seen": len(self.seen_ids),
            "listing_docs": {str(k): list(v) for k, v in self.listing_docs.items()},
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

    def _extract_doc_keys(self, listing: Dict[str, Any]) -> Set[str]:
        """Extract unique document identifiers from a listing"""
        doc_keys = set()
        for link in listing.get("ls", []):
            doc_url = link.get("u2", "") or link.get("u1", "")
            if doc_url:
                doc_keys.add(doc_url)
        return doc_keys

    def detect_new_listings(
        self, listings: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Detect new listings and document updates"""
        new_listings = []
        updated_listings = []
        current_ids = set()

        # Skip sending update alerts if this is first run with document tracking
        skip_update_alerts = not self.docs_tracking_initialized

        for listing in listings:
            listing_id = listing.get("id")
            if not listing_id:
                continue

            current_ids.add(listing_id)
            current_doc_keys = self._extract_doc_keys(listing)

            if listing_id not in self.seen_ids:
                # Completely new listing
                new_listings.append(listing)
                logger.info(f"New listing: {listing.get('a')} (ID: {listing_id})")
            else:
                # Existing listing - check for new documents
                stored_doc_keys = self.listing_docs.get(listing_id, set())
                new_docs = current_doc_keys - stored_doc_keys
                if new_docs:
                    # Only add to updated_listings if we should send alerts
                    if not skip_update_alerts:
                        updated_listings.append(listing)
                    logger.info(
                        f"Document update: {listing.get('a')} (ID: {listing_id}) - "
                        f"{len(new_docs)} new document(s)"
                        + (" (alert skipped - first run)" if skip_update_alerts else "")
                    )

            # Update document tracking
            self.listing_docs[listing_id] = current_doc_keys

        # Update seen IDs with all current listings
        self.seen_ids.update(current_ids)

        # Mark document tracking as initialized after first run
        if not self.docs_tracking_initialized:
            self.docs_tracking_initialized = True
            logger.info(
                "Document tracking initialized - future updates will trigger alerts"
            )

        total_changes = len(new_listings) + (
            len(updated_listings) if not skip_update_alerts else 0
        )
        if total_changes > 0:
            logger.info(
                f"Detected {len(new_listings)} new listings, "
                f"{len(updated_listings)} updated (alerts will be sent)"
            )
        else:
            logger.debug("No new listings or updates detected")

        return new_listings, updated_listings

    def format_telegram_message(
        self, listing: Dict[str, Any], is_update: bool = False
    ) -> str:
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

        # Build pre-submission document links (ps field)
        pre_sub_links = []
        ps_links = listing.get("ps", [])

        for link in ps_links:
            doc_date = link.get("d", "")
            doc_name = link.get("nS1", "前提交文件")
            doc_url = link.get("u1", "")

            if doc_url:
                if doc_url.startswith("http"):
                    full_url = doc_url
                else:
                    full_url = f"https://www1.hkexnews.hk/app/{doc_url}"

                pre_sub_links.append(f"• [{doc_name}]({full_url})")

        # Format status
        status_text = {
            "A": "Active (Application Proof)",
            "I": "Inactive",
            "W": "Withdrawn",
        }.get(status, status)

        # Change message header based on type
        if is_update:
            message_header = "🔄 **HKEX Listing Document Update!**"
        else:
            message_header = "🚨 **New HKEX Listing Detected!**"

        # Build message
        message = f"""{message_header}

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

        # Add pre-submission documents section if available
        if pre_sub_links:
            message += f"""

📑 **前提交文件:**
{chr(10).join(pre_sub_links)}"""

        message += f"""

[View All Listings](https://www1.hkexnews.hk/app/appindex.html?lang=zh)

_Detected at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}_"""

        return message

    async def send_telegram_alerts(
        self, listings: List[Dict[str, Any]], is_update: bool = False
    ) -> None:
        """Send Telegram alerts for new listings or updates"""
        for listing in listings:
            try:
                message = self.format_telegram_message(listing, is_update=is_update)
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=False,
                )
                logger.info(
                    f"Sent {'update' if is_update else 'new'} alert for listing ID {listing.get('id')}"
                )

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

        new_listings, updated_listings = self.detect_new_listings(listings)

        if new_listings:
            logger.info(f"Sending alerts for {len(new_listings)} new listings")
            await self.send_telegram_alerts(new_listings, is_update=False)

        if updated_listings:
            logger.info(f"Sending alerts for {len(updated_listings)} document updates")
            await self.send_telegram_alerts(updated_listings, is_update=True)

        if not new_listings and not updated_listings:
            logger.info("No new listings or updates to report")

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
