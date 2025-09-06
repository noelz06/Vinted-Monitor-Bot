import asyncio
import aiohttp
import json
import logging
import os
import sys
import signal
import pickle
import re
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib
import time
import random
from urllib.parse import urlencode, quote, urlparse
from collections import defaultdict, deque
from contextlib import asynccontextmanager
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
import traceback

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

def setup_logging(log_level=logging.INFO, log_file='vinted_bot.log'):
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    ))
    file_handler.setLevel(log_level)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredFormatter(
        fmt='%(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    ))
    
    logging.basicConfig(
        level=log_level,
        handlers=[file_handler, console_handler]
    )
    
    return logging.getLogger(__name__)

logger = setup_logging(log_level=logging.DEBUG)

@dataclass
class SearchFilters:
    query: str
    sizes: List[str] = field(default_factory=list)
    gender: Optional[str] = None
    category: str = "Clothing"
    max_days_old: int = 0
    
    def matches_item(self, item: Dict) -> Tuple[bool, str]:
        if self.category == "Clothing" and self.sizes:
            item_size = item.get('size_title', '').strip().upper()
            if not item_size:
                return False, f"Size mismatch: {item_size}"
            
            size_match = False
            for target_size in self.sizes:
                if target_size.upper() == item_size or target_size.upper() in item_size.split(' / '):
                    size_match = True
                    break
            
            if not size_match:
                return False, f"Size mismatch: {item_size}"
        
        return True, "All filters matched"

@dataclass
class SearchConfig:
    chat_id: str
    filters: SearchFilters
    name: str = "Unnamed Search"
    enabled: bool = True
    notification_settings: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    items_found: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'chat_id': self.chat_id,
            'name': self.name,
            'enabled': self.enabled,
            'filters': {
                'query': self.filters.query,
                'sizes': self.filters.sizes,
                'gender': self.filters.gender,
                'category': self.filters.category
            },
            'notification_settings': self.notification_settings,
            'created_at': self.created_at.isoformat(),
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'items_found': self.items_found
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SearchConfig':
        filters = SearchFilters(
            query=data['filters']['query'],
            sizes=data['filters'].get('sizes', []),
            gender=data['filters'].get('gender') if data['filters'].get('category', 'Clothing') == 'Clothing' else None,
            category=data['filters'].get('category', 'Clothing')
        )
        
        return cls(
            chat_id=data['chat_id'],
            filters=filters,
            name=data.get('name', 'Unnamed Search'),
            enabled=data.get('enabled', True),
            notification_settings=data.get('notification_settings', {}),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now(),
            last_run=datetime.fromisoformat(data['last_run']) if data.get('last_run') else None,
            items_found=data.get('items_found', 0)
        )

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(deque)
        self.lock = threading.Lock()
    
    def can_request(self, endpoint: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
        current_time = time.time()
        
        with self.lock:
            endpoint_requests = self.requests[endpoint]
            
            while endpoint_requests and current_time - endpoint_requests[0] >= window_seconds:
                endpoint_requests.popleft()
            
            if len(endpoint_requests) >= max_requests:
                return False
            
            endpoint_requests.append(current_time)
            return True

class SessionManager:
    def __init__(self, country_code: str = '.hu'):
        self.country_code = country_code
        self.base_url = f"https://www.vinted{country_code}"
        self.api_base = f"https://www.vinted{country_code}/api/v2"
        self.session = None
        self.cookies = {}
        self.headers = self.get_default_headers()
        self.last_cookie_refresh = 0
        self.session_lock = asyncio.Lock()
        
    def get_default_headers(self) -> Dict[str, str]:
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
        ]
        
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
    
    def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
            self.headers = self.get_default_headers()
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=self.headers,
                cookies=self.cookies
            )
        return self.session
    
    async def refresh_cookies(self):
        async with self.session_lock:
            try:
                session = self.get_session()
                async with session.get(self.base_url) as response:
                    if response.status == 200:
                        self.cookies.update(session.cookie_jar._cookies)
                        self.last_cookie_refresh = time.time()
                        logger.debug(f"Refreshed cookies: {len(self.cookies)} cookies")
                    else:
                        logger.warning(f"Failed to refresh cookies: {response.status}")
            except Exception as e:
                logger.error(f"Cookie refresh error: {e}")
    
    def get_headers(self, referer: str = None) -> Dict[str, str]:
        headers = self.headers.copy()
        if referer:
            headers['Referer'] = referer
        return headers
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

class VintedAPI:
    def __init__(self, session_manager: SessionManager, rate_limiter: RateLimiter):
        self.session_manager = session_manager
        self.rate_limiter = rate_limiter
        self.api_endpoints = {
            'search': '/catalog/items',
            'item': '/items/{item_id}',
        }
    
    async def search(self, filters: SearchFilters, page: int = 1, per_page: int = 20) -> List[Dict]:
        if not self.rate_limiter.can_request('search', max_requests=20, window_seconds=60):
            logger.warning("Rate limit reached for search")
            await asyncio.sleep(random.uniform(5, 10))
            return []
        
        params = {
            'page': str(page),
            'per_page': str(per_page),
            'order': 'newest_first',
            'search_text': filters.query
        }
        
        if filters.category == "Clothing":
            if filters.gender == "Men":
                params['catalog_ids'] = '5'
            elif filters.gender == "Women":
                params['catalog_ids'] = '1'
        
        url = f"{self.session_manager.api_base}{self.api_endpoints['search']}"
        query_string = urlencode(params, quote_via=quote)
        full_url = f"{url}?{query_string}"
        
        try:
            if time.time() - self.session_manager.last_cookie_refresh > 60:
                await self.session_manager.refresh_cookies()
            
            await asyncio.sleep(random.uniform(0.5, 2))
            
            session = self.session_manager.get_session()
            headers = self.session_manager.get_headers(referer=f"{self.session_manager.base_url}/catalog")
            
            logger.debug(f"Link: {full_url}")
            
            async with session.get(full_url, headers=headers) as response:
                logger.debug(f"Search response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    items = data.get('items', [])
                    logger.info(f"Found {len(items)} items for query: {filters.query}")
                    
                    filtered_items = []
                    for item in items:
                        matches, reason = filters.matches_item(item)
                        if matches:
                            filtered_items.append(item)
                        else:
                            logger.debug(f"Item filtered out: {reason}")
                    
                    logger.info(f"After filtering: {len(filtered_items)} items")
                    return filtered_items
                
                elif response.status == 429:
                    logger.warning("Rate limited by Vinted API")
                    await asyncio.sleep(random.uniform(10, 20))
                    return []
                
                elif response.status == 403:
                    logger.warning("Forbidden - refreshing session")
                    await self.session_manager.refresh_cookies()
                    return []
                
                else:
                    logger.error(f"API error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

class TelegramNotifier:
    def __init__(self, token: str, country_code: str = '.hu'):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.sent_items: Set[str] = set()
        self.vinted_base_url = f"https://www.vinted{country_code}"
    
    async def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML"):
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.debug(f"Message sent successfully to chat {chat_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to send message: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Telegram API error: {e}")
            return False
    
    def format_item(self, item: Dict) -> str:
        title = item.get('title', 'Unknown')
        item_id = item.get('id', '')
        url = f"{self.vinted_base_url}/items/{item_id}"
        
        price_info = item.get('price', {})
        currency_code = price_info.get('currency_code', 'EUR')
        amount = price_info.get('amount', 'N/A')
        
        size = item.get('size_title', 'N/A')
        brand = item.get('brand_title', 'N/A')
        condition = item.get('status', 'N/A')
        user_login = item.get('user', {}).get('login', 'N/A')
        
        photos = item.get('photos', [])
        photo_url = photos[0].get('url') if photos else None
        
        message = f"<b>{title}</b>\n"
        message += f"💰 Price: {amount} {currency_code}\n"
        message += f"📏 Size: {size}\n"
        message += f"🏷️ Brand: {brand}\n"
        message += f"⚡ Condition: {condition}\n"
        message += f"👤 Seller: {user_login}\n"
        message += f"🔗 <a href='{url}'>View Item</a>\n"
        
        if photo_url:
            message += f"📸 <a href='{photo_url}'>Photo</a>\n"
        
        return message
    
    def generate_item_hash(self, item: Dict) -> str:
        unique_string = f"{item.get('id', '')}-{item.get('title', '')}-{item.get('price', {}).get('amount', 0)}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    async def notify_new_items(self, items: List[Dict], chat_id: str):
        new_items = []
        
        for item in items:
            item_hash = self.generate_item_hash(item)
            if item_hash not in self.sent_items:
                new_items.append(item)
                self.sent_items.add(item_hash)
        
        if not new_items:
            logger.debug("No new items to send")
            return
        
        logger.info(f"Sending {len(new_items)} new items to chat {chat_id}")
        
        for item in new_items:
            message = self.format_item(item)
            success = await self.send_message(chat_id, message)
            if success:
                logger.debug(f"Sent notification for item: {item.get('title', 'Unknown')}")
            else:
                logger.error(f"Failed to send notification for item: {item.get('title', 'Unknown')}")
            
            await asyncio.sleep(1)

class VintedBot:
    def __init__(self, config_path: str = 'config.json'):
        self.config_path = config_path
        self.config = self.load_config()
        
        country_code = self.config.get('country_code', '.hu')
        
        self.rate_limiter = RateLimiter()
        self.session_manager = SessionManager(country_code)
        self.api = VintedAPI(self.session_manager, self.rate_limiter)
        self.notifier = TelegramNotifier(self.config['telegram_token'], country_code)
        
        self.searches: List[SearchConfig] = []
        self.load_searches()
        
        self.running = False
        self.check_interval = 50
    
    def load_config(self) -> Dict:
        try:
            if not os.path.exists(self.config_path):
                logger.info("Config file not found, creating initial setup")
                return self.create_initial_config()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            required_keys = ['telegram_token']
            missing_keys = [key for key in required_keys if key not in config]
            if missing_keys:
                logger.error(f"Missing required config keys: {missing_keys}")
                sys.exit(1)
            
            logger.info("Configuration loaded successfully")
            return config
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            sys.exit(1)
            
        except KeyError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
    
    def create_initial_config(self) -> Dict:
        print("\n🎉 Welcome to Vinted Monitor Bot Setup!")
        print("=" * 40)
        
        telegram_token = input("🤖 Enter your Telegram Bot Token: ").strip()
        if not telegram_token:
            logger.error("Telegram token cannot be empty!")
            sys.exit(1)
        
        print("\n🌍 Select country:")
        print("🇭🇺 1. Hungary (.hu)")
        print("🇩🇪 2. Germany (.de)")
        print("🇫🇷 3. France (.fr)")
        print("🇬🇧 4. UK/International (.com)")
        print("🇪🇸 5. Spain (.es)")
        
        country_choice = input("Choose (1-5): ").strip()
        country_codes = {'1': '.hu', '2': '.de', '3': '.fr', '4': '.com', '5': '.es'}
        country_code = country_codes.get(country_choice, '.hu')
        
        config = {
            "telegram_token": telegram_token,
            "country_code": country_code,
            "searches": []
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Configuration saved to {self.config_path}")
        print("📝 You can now add searches using the menu!")
        
        return config
    
    def load_searches(self):
        if 'searches' in self.config and self.config['searches']:
            for search_data in self.config['searches']:
                search_config = SearchConfig(
                    chat_id=search_data.get('chat_id'),
                    name=f"Search: {search_data.get('query', 'Unknown')}",
                    filters=SearchFilters(
                        query=search_data.get('query', ''),
                        sizes=search_data.get('size_titles', []),
                        gender=search_data.get('gender') if search_data.get('category', 'Clothing') == 'Clothing' else None,
                        category=search_data.get('category', 'Clothing')
                    )
                )
                self.searches.append(search_config)
            
            logger.info(f"Loaded {len(self.searches)} searches from config.json")
        else:
            print("\nNo searches found in config.json. Let's create one!")
    
    def save_searches(self):
        searches_data = []
        for search in self.searches:
            search_dict = {
                "chat_id": search.chat_id,
                "query": search.filters.query,
                "size_titles": search.filters.sizes,
                "category": search.filters.category
            }
            if search.filters.category == "Clothing" and search.filters.gender:
                search_dict["gender"] = search.filters.gender
            searches_data.append(search_dict)
        
        self.config['searches'] = searches_data
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def generate_item_hash(self, item: Dict) -> str:
        unique_string = f"{item.get('id', '')}-{item.get('title', '')}-{item.get('price', {}).get('amount', 0)}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    async def process_search(self, search_config: SearchConfig):
        if not search_config.enabled:
            return
        
        logger.info(f"Processing search: {search_config.name}")
        
        try:
            items = await self.api.search(search_config.filters, per_page=20)
            
            if items:
                search_config.items_found = len(items)
                search_config.last_run = datetime.now()
                await self.notifier.notify_new_items(items, search_config.chat_id)
            
        except Exception as e:
            logger.error(f"Error processing search '{search_config.name}': {e}")
            logger.debug(traceback.format_exc())
    
    async def start(self):
        self.running = True
        logger.info("Starting Vinted Monitor Bot")
        
        if not self.searches:
            print("\n❌ No searches configured! Please add at least one search before starting monitoring.")
            print("💡 Go back to the menu and select '1. Add new search' first.")
            input("\nPress Enter to return to menu...")
            return
        
        logger.info(f"Monitoring {len(self.searches)} searches every {self.check_interval} seconds")
        
        while self.running:
            try:
                start_time = time.time()
                
                tasks = [self.process_search(search) for search in self.searches if search.enabled]
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                if self.running:
                    elapsed_time = time.time() - start_time
                    print(f"\n⏱️ Search completed in {elapsed_time:.2f}s")
                    print(f"⏳ Next check in {self.check_interval}s...")
                    await asyncio.sleep(self.check_interval)
                    
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                await asyncio.sleep(60)
    
    async def stop(self):
        logger.info("Stopping bot...")
        self.running = False
        await self.session_manager.close()
        logger.info("Bot stopped")
    
    def display_current_searches(self):
        if not self.searches:
            print("\nNo searches configured")
            return
            
        print(f"\n📋 Current searches ({len(self.searches)}):")
        print("=" * 50)
        
        for i, search in enumerate(self.searches, 1):
            print(f"{i}. {search.name}")
            print(f"   💬 Chat ID: {search.chat_id}")
            print(f"   🔍 Query: {search.filters.query}")
            print(f"   📦 Category: {search.filters.category}")
            if search.filters.category == "Clothing" and search.filters.gender:
                print(f"   👔 Gender: {search.filters.gender}")
            if search.filters.category == "Clothing" and search.filters.sizes:
                print(f"   📏 Sizes: {', '.join(search.filters.sizes)}")
            print(f"   ✅ Enabled: {search.enabled}")
            print(f"   🔢 Items found: {search.items_found}")
            print()
    
    def create_search_config(self) -> Optional[SearchConfig]:
        print("\n➕ Creating new search:")
        print("-" * 30)
        
        print("📦 Select category:")
        print("1. Clothing")
        print("2. Other")
        category_choice = input("Choose (1-2): ").strip()
        
        if category_choice == '1':
            category = 'Clothing'
        elif category_choice == '2':
            category = 'Other'
        else:
            print("Invalid choice, defaulting to Clothing")
            category = 'Clothing'
        
        query = input("\n🔍 Search query (e.g., 'ralph lauren'): ").strip()
        if not query:
            print("Query cannot be empty!")
            return None
        
        chat_id = input("💬 Telegram Chat ID: ").strip()
        if not chat_id:
            print("Chat ID cannot be empty!")
            return None
        
        sizes = []
        gender = None
        
        if category == 'Clothing':
            sizes_input = input("📏 Sizes (comma-separated, e.g., 'S,M,L' or press Enter for any): ").strip()
            sizes = [size.strip().upper() for size in sizes_input.split(',') if size.strip()] if sizes_input else []
            
            print("\n👔 Select gender:")
            print("1. Men")
            print("2. Women")
            gender_choice = input("Choose (1-2): ").strip()
            
            if gender_choice == '1':
                gender = 'Men'
            elif gender_choice == '2':
                gender = 'Women'
            else:
                print("Invalid choice, defaulting to Men")
                gender = 'Men'
        else:
            print("For 'Other' category, no size or gender filtering is applied.")
        
        search_config = SearchConfig(
            chat_id=chat_id,
            name=f"Search: {query}",
            filters=SearchFilters(
                query=query,
                sizes=sizes,
                gender=gender,
                category=category
            )
        )
        
        return search_config
    
    def remove_search(self):
        if not self.searches:
            print("\nNo searches to remove")
            return
        
        self.display_current_searches()
        
        try:
            choice = int(input(f"\nEnter search number to remove (1-{len(self.searches)}): "))
            if 1 <= choice <= len(self.searches):
                removed = self.searches.pop(choice - 1)
                self.save_searches()
                print(f"✅ Removed search: {removed.name}")
            else:
                print("Invalid choice")
        except ValueError:
            print("Invalid input")
    
    def setup_country_code(self):
        current = self.config.get('country_code', '.hu')
        print(f"\n🌍 Current country: {current}")
        print("\nAvailable countries:")
        print("🇭🇺 .hu - Hungary")
        print("🇩🇪 .de - Germany") 
        print("🇫🇷 .fr - France")
        print("🇬🇧 .com - UK/International")
        print("🇪🇸 .es - Spain")
        
        new_code = input("\nEnter new country code (or press Enter to keep current): ").strip()
        
        if new_code and new_code in ['.hu', '.de', '.fr', '.com', '.es']:
            self.config['country_code'] = new_code
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"✅ Country code updated to: {new_code}")
            print("⚠️  Please restart the bot for changes to take effect!")
        elif new_code:
            print("Invalid country code")
        else:
            print("⏭️  Country code unchanged")
    
    async def interactive_menu(self):
        while True:
            self.display_current_searches()
            print(f"\n🌍 Current country: {self.config.get('country_code', '.hu')}")
            
            print("\nWhat would you like to do?")
            print("1. ➕ Add new search")
            print("2. ❌ Remove search") 
            print("3. 🌍 Change country")
            print("4. 🚀 Start monitoring")
            print("5. 🚪 Exit")
            
            choice = input("\nChoose option (1-5): ").strip()
            
            if choice == '1':
                search = self.create_search_config()
                if search:
                    self.searches.append(search)
                    self.save_searches()
                    print("✅ Search added successfully!")
            elif choice == '2':
                self.remove_search()
            elif choice == '3':
                self.setup_country_code()
            elif choice == '4':
                if not self.searches:
                    print("\n❌ No searches configured!")
                    print("💡 Please add at least one search first (option 1)")
                    continue
                    
                print("\n🚀 Starting monitoring in 3 seconds...")
                print("Press Ctrl+C to stop")
                await asyncio.sleep(3)
                await self.start()
                break
            elif choice == '5':
                print("👋 Goodbye!")
                return
            else:
                print("Invalid choice")

async def main():
    bot = VintedBot()
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        loop = asyncio.get_event_loop()
        loop.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print("\n🤖 Vinted Monitor Bot")
        print("=" * 40)
        await bot.interactive_menu()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug(traceback.format_exc())
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
