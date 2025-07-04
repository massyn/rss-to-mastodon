import yaml
import feedparser
import dateparser
import datetime
import re
import os
import logging
import time
import hashlib
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from mastodon import Mastodon
import socket
from dotenv import load_dotenv

load_dotenv()
socket.setdefaulttimeout(10)          # seconds  ← change once, applies everywhere
logging.basicConfig(
    level="DEBUG",
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)

@dataclass
class FeedItem:
    feed_title: str
    title: str
    summary: str
    link: str
    published_date: datetime.datetime
    content_hash: str
    
    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.md5(f"{self.link}{self.title}".encode()).hexdigest()

class RSSReader:
    def __init__(self, max_retries: int = 3, retry_delay: int = 5):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
    def read_rss(self, feed_url: str) -> Optional[feedparser.FeedParserDict]:
        logging.info(f"Reading RSS feed {feed_url}")
        
        for attempt in range(self.max_retries):
            try:
                feed = feedparser.parse(feed_url, agent=self.user_agent)
                
                if feed.bozo and feed.bozo_exception:
                    logging.warning(f" --> Feed parse warning: {feed.bozo_exception}")
                    
                entry_count = len(feed.get('entries', []))
                logging.info(f" --> Found {entry_count} items...")
                
                if entry_count == 0:
                    logging.warning(f" --> No entries found in feed")
                    
                return feed
                
            except socket.timeout:
                logging.warning(f" --> Attempt {attempt + 1} timed out after 10s")
            except Exception as exc:
                logging.error(f" --> Attempt {attempt + 1} failed: {exc}")
                
            if attempt < self.max_retries - 1:
                logging.info(f" --> Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
                
        logging.error(f" --> Failed to read feed after {self.max_retries} attempts")
        return None

    def filter_rss(self, feed: Optional[feedparser.FeedParserDict], latest: datetime.datetime) -> List[FeedItem]:
        data = []
        if feed is None:
            return data
            
        feed_title = feed.get('feed', {}).get('title', 'No title')
        
        for entry in feed.get('entries', []):
            try:
                # Check for required fields
                if 'published' not in entry:
                    logging.debug(f"Skipping entry without published date: {entry.get('title', 'No title')}")
                    continue
                    
                # Parse published date with better error handling
                published_date = self._parse_date(entry['published'])
                if published_date is None:
                    logging.warning(f"Could not parse date for entry: {entry.get('title', 'No title')}")
                    continue
                    
                # Filter by date
                if published_date <= latest:
                    continue
                    
                # Extract and clean content
                title = entry.get('title', 'No title').strip()
                summary = self._clean_html(entry.get('summary', entry.get('description', '')))
                link = entry.get('link', '')
                
                if not link:
                    logging.warning(f"Skipping entry without link: {title}")
                    continue
                    
                item = FeedItem(
                    feed_title=feed_title,
                    title=title,
                    summary=summary,
                    link=link,
                    published_date=published_date,
                    content_hash=''
                )
                
                data.append(item)
                
            except Exception as e:
                logging.error(f"Error processing entry: {e}")
                continue
                
        return data
        
    def _parse_date(self, date_str: str) -> Optional[datetime.datetime]:
        try:
            return dateparser.parse(date_str, settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True})
        except Exception as e:
            logging.error(f"Date parsing failed for '{date_str}': {e}")
            return None
            
    def _clean_html(self, text: str) -> str:
        if not text:
            return ''
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove common HTML entities
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return text.strip()

class MessageFormatter:
    def __init__(self, max_length: int = 10000):
        self.max_length = max_length
        
    def format_individual(self, item: FeedItem) -> str:
        emoji = self._get_feed_emoji(item.feed_title)
        
        # Truncate summary if needed
        summary = self._truncate_text(item.summary, 800)
        
        msg = f"{emoji} {item.feed_title}\n\n{item.title}\n\n{summary}\n\n🔗 {item.link}"
        
        return self._truncate_text(msg, self.max_length)
        
    def format_digest(self, items: List[FeedItem], section: str) -> str:
        date_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
        feed_count = len(set(item.feed_title for item in items))
        
        msg = f"🔒 Security News Digest - {date_str}\n\n"
        msg += f"📊 {len(items)} updates from {feed_count} sources:\n\n"
        
        for item in items:
            emoji = self._get_feed_emoji(item.feed_title)
            msg += f"{emoji} {item.feed_title}: {item.title}\n   {item.link}\n\n"
            
        msg += "#InfoSec #SecurityNews"
        
        return self._truncate_text(msg, self.max_length)
        
    def _get_feed_emoji(self, feed_title: str) -> str:
        feed_title_lower = feed_title.lower()
        if 'aws' in feed_title_lower or 'amazon' in feed_title_lower:
            return '☁️'
        elif 'microsoft' in feed_title_lower or 'azure' in feed_title_lower:
            return '🪟'
        elif 'google' in feed_title_lower:
            return '🔍'
        elif 'cisa' in feed_title_lower or 'government' in feed_title_lower:
            return '🏛️'
        elif 'malware' in feed_title_lower:
            return '🦠'
        else:
            return '🔹'
            
    def _truncate_text(self, text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
            
        # Find the last space before max_length to avoid cutting words
        truncate_at = text.rfind(' ', 0, max_length - 3)
        if truncate_at == -1:
            truncate_at = max_length - 3
            
        return text[:truncate_at] + '...'

class MastodonClient:
    def __init__(self, endpoint: str, access_token: str, max_retries: int = 3):
        self.endpoint = endpoint
        self.access_token = access_token
        self.max_retries = max_retries
        self.mastodon = None
        self.account_info = None
        
    def authenticate(self) -> bool:
        try:
            self.mastodon = Mastodon(
                api_base_url=self.endpoint,
                access_token=self.access_token
            )
            self.account_info = self.mastodon.account_verify_credentials()
            logging.info(f"Authenticated as {self.account_info.get('display_name')} ({self.account_info.get('id')})")
            return True
        except Exception as e:
            logging.error(f"Authentication failed: {e}")
            return False
            
    def get_last_post_time(self) -> Optional[datetime.datetime]:
        if not self.mastodon or not self.account_info:
            return None
            
        try:
            statuses = self.mastodon.account_statuses(id=self.account_info.get('id'), limit=1)
            if len(statuses) == 0:
                logging.info("No previous posts found")
                return None
            return statuses[0]['created_at']
        except Exception as e:
            logging.error(f"Failed to get last post time: {e}")
            return None
            
    def post_status(self, content: str) -> bool:
        if not self.mastodon:
            logging.error("Not authenticated")
            return False
            
        for attempt in range(self.max_retries):
            try:
                self.mastodon.status_post(content)
                logging.info("Status posted successfully")
                return True
            except Exception as e:
                logging.error(f"Post attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
        logging.error(f"Failed to post status after {self.max_retries} attempts")
        return False
        
    def post_welcome_message(self) -> bool:
        return self.post_status("🔒 RSS Security Bot is now active! Stay tuned for security news updates.")


class RSSMastodonBot:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        self.rss_reader = RSSReader()
        self.formatter = MessageFormatter()
        self.seen_items: Set[str] = set()  # In-memory deduplication
        
    def _load_config(self) -> Dict:
        try:
            with open(self.config_path, 'rt') as f:
                config = yaml.safe_load(f)
            if not config:
                raise ValueError("Empty configuration file")
            return config
        except Exception as e:
            logging.error(f"Could not read {self.config_path}: {e}")
            raise
            
    def _get_fallback_timestamp(self) -> datetime.datetime:
        hours_back = int(os.environ.get('RSS_FALLBACK_HOURS', '6'))
        return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours_back)
        
    def _deduplicate_items(self, items: List[FeedItem]) -> List[FeedItem]:
        unique_items = []
        for item in items:
            if item.content_hash not in self.seen_items:
                self.seen_items.add(item.content_hash)
                unique_items.append(item)
            else:
                logging.debug(f"Skipping duplicate item: {item.title}")
        return unique_items
        
    def run(self):
        logging.info("Starting RSS Mastodon Bot")
        
        for section in self.config:
            logging.info(f"Processing section: {section}")
            
            # Check environment variables
            endpoint = os.environ.get(f"{section}_ENDPOINT")
            access_token = os.environ.get(f"{section}_ACCESS_TOKEN")
            
            if not endpoint:
                logging.error(f"Environment variable {section}_ENDPOINT is not set")
                continue
            if not access_token:
                logging.error(f"Environment variable {section}_ACCESS_TOKEN is not set")
                continue
                
            # Initialize Mastodon client
            client = MastodonClient(endpoint, access_token)
            if not client.authenticate():
                logging.error(f"Failed to authenticate for section {section}")
                continue
                
            # Get last post time or use fallback
            last_post_time = client.get_last_post_time()
            if last_post_time is None:
                logging.info(f"No previous posts found for {section}, posting welcome message")
                client.post_welcome_message()
                continue
                
            logging.info(f"Last post time for {section}: {last_post_time}")
            
            # Process RSS feeds
            all_items = []
            for rss_url in self.config[section]:
                logging.info(f"Processing RSS feed: {rss_url}")
                
                feed = self.rss_reader.read_rss(rss_url)
                items = self.rss_reader.filter_rss(feed, last_post_time)
                all_items.extend(items)
                
            # Deduplicate items
            unique_items = self._deduplicate_items(all_items)
            
            if not unique_items:
                logging.info(f"No new items found for section {section}")
                continue
                
            # Sort by publication date
            unique_items.sort(key=lambda x: x.published_date)
            
            # Post items
            digest_threshold = int(os.environ.get('RSS_DIGEST_THRESHOLD', '5'))
            
            if len(unique_items) < digest_threshold:
                logging.info(f"Posting {len(unique_items)} individual items")
                for item in unique_items:
                    msg = self.formatter.format_individual(item)
                    logging.info(f"Posting: {item.title}")
                    client.post_status(msg)
                    time.sleep(1)  # Rate limiting
            else:
                logging.info(f"Posting digest with {len(unique_items)} items")
                msg = self.formatter.format_digest(unique_items, section)
                client.post_status(msg)
                
        logging.info("RSS Mastodon Bot completed")
        
    def test_mode(self):
        logging.info("Running in test mode - no posts will be made")
        
        for section in self.config:
            logging.info(f"Testing section: {section}")
            
            # Use fallback timestamp for testing
            test_timestamp = self._get_fallback_timestamp()
            logging.info(f"Using test timestamp: {test_timestamp}")
            
            all_items = []
            for rss_url in self.config[section]:
                logging.info(f"Testing RSS feed: {rss_url}")
                
                feed = self.rss_reader.read_rss(rss_url)
                items = self.rss_reader.filter_rss(feed, test_timestamp)
                all_items.extend(items)
                
            unique_items = self._deduplicate_items(all_items)
            
            if not unique_items:
                logging.info(f"No items found for section {section}")
                continue
                
            unique_items.sort(key=lambda x: x.published_date)
            
            digest_threshold = int(os.environ.get('RSS_DIGEST_THRESHOLD', '5'))
            
            if len(unique_items) < digest_threshold:
                logging.info(f"Would post {len(unique_items)} individual items:")
                for item in unique_items:
                    msg = self.formatter.format_individual(item)
                    print(f"\n--- Individual Post ---\n{msg}\n")
            else:
                logging.info(f"Would post digest with {len(unique_items)} items:")
                msg = self.formatter.format_digest(unique_items, section)
                print(f"\n--- Digest Post ---\n{msg}\n")
                
        logging.info("Test mode completed")


def main(config_path: str):
    bot = RSSMastodonBot(config_path)
    bot.run()
    
def test(config_path: str):
    bot = RSSMastodonBot(config_path)
    bot.test_mode()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test('config.yaml')
    else:
        main('config.yaml')