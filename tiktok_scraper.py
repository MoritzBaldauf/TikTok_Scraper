from playwright.sync_api import sync_playwright
import pandas as pd
from datetime import datetime, timedelta
import os
import time
import random
from config import *
from credentials.cookies_config import get_tiktok_cookies
import logging

class TikTokScraper:
    def __init__(self, account_name):
        self.account_name = account_name
        self.account_url = f"https://www.tiktok.com/@{account_name}"
        self.setup_data_directories()
        
    def setup_data_directories(self):
        """Create necessary directories for data storage"""
        self.account_data_dir = os.path.join(DATA_DIR, self.account_name)
        os.makedirs(self.account_data_dir, exist_ok=True)
        
    def start_browser(self):
        """Initialize the browser with enhanced anti-detection measures"""
        self.playwright = sync_playwright().start()
        
        # Enhanced browser arguments
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
            '--disable-web-security',
            '--disable-features=IsolateOrigins',
            '--disable-site-isolation-trials',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--ignore-certificate-errors'
        ]
        
        self.browser = self.playwright.chromium.launch(
            headless=HEADLESS_MODE,
            args=browser_args
        )
        
        # Enhanced context configuration
        self.context = self.browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1280, 'height': 800},
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],
            java_script_enabled=True,
            bypass_csp=True,
            color_scheme='light',
            reduced_motion='no-preference',
            forced_colors='none',
            accept_downloads=False
        )
        
        # Modify navigator properties
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        # Get cookies from the separate configuration file
        cookies = get_tiktok_cookies()
        self.context.add_cookies(cookies)
        
        # Create new page after setting cookies
        self.page = self.context.new_page()
        
        # Add additional page configurations
        self.page.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        })


    def scrape_account_metrics(self):
        """Scrape basic account information with session rotation"""
        if not self.load_page_with_retry(self.account_url):
            logging.error("Failed to load account page after all retries")
            return None
            
        try:
            # Add some random delays and movements before extracting data
            self._simulate_human_behavior()
            
            current_time = datetime.now()
            metrics = {
                'date': current_time.strftime('%Y-%m-%d'),
                'scrape_timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                'account_name': self.account_name,
                'follower_count': self._extract_follower_count(),
                'total_likes': self._extract_total_likes()
            }
            
            if all(value != 0 for value in metrics.values() if isinstance(value, (int, float))):
                self._save_account_metrics(metrics)
                return metrics
                
            logging.error("Failed to get complete metrics")
            return None
            
        except Exception as e:
            logging.error(f"Error scraping account metrics: {str(e)}")
            return None
    def scrape_recent_videos(self):
        """Scrape videos with session rotation support"""
        try:
            videos = []
            current_time = datetime.now()
            
            # Ensure page is loaded with content
            if not self.load_page_with_retry(self.account_url):
                logging.error("Failed to load videos page after all retries")
                return []
                
            # Add some random delays and movements
            self._simulate_human_behavior()
            
            # Scroll a few times to load more videos
            scroll_attempts = 3
            for _ in range(scroll_attempts):
                # Get current video elements
                video_elements = self.page.query_selector_all('div[data-e2e="user-post-item"]')
                
                for element in video_elements:
                    if len(videos) > 0 and any(v['video_id'] == element.get_attribute('data-video-id') for v in videos):
                        continue  # Skip already processed videos
                        
                    video_data = self._extract_video_data(element)
                    if video_data:
                        # Skip pinned videos if configured to do so
                        if EXCLUDE_PINNED_VIDEOS and video_data['is_pinned']:
                            continue
                            
                        # Add scrape timestamp to video data
                        video_data['scrape_timestamp'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
                        videos.append(video_data)
                        
                        # Stop if we've found a video older than 24 hours
                        if not video_data['is_new'] and not video_data['is_pinned']:
                            break
                            
                    # Add random delay between video processing
                    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
                
                # If we found an old video, stop scrolling
                if videos and not videos[-1]['is_new'] and not videos[-1]['is_pinned']:
                    break
                    
                # Scroll to load more with improved waiting
                if not self._scroll_and_wait():
                    break
            
            self._save_video_metrics(videos)
            return videos
            
        except Exception as e:
            logging.error(f"Error scraping videos: {str(e)}")
            return []

    def _simulate_human_behavior(self):
        """Simulate human-like behavior to avoid detection"""
        # Random mouse movements
        for _ in range(random.randint(3, 7)):
            self.page.mouse.move(
                random.randint(100, 800),
                random.randint(100, 600),
                steps=random.randint(5, 10)
            )
            time.sleep(random.uniform(0.1, 0.3))
        
        # Random scrolling
        self.page.mouse.wheel(0, random.randint(300, 700))
        time.sleep(random.uniform(0.5, 1.5))

    def _extract_follower_count(self):
        """Extract follower count with retry logic"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                follower_element = self.page.wait_for_selector('strong[data-e2e="followers-count"]', 
                                                             timeout=DEFAULT_TIMEOUT)
                if follower_element:
                    follower_text = follower_element.text_content()
                    count = self._convert_count_to_number(follower_text)
                    if count > 0:
                        return count
                raise Exception("Failed to get valid follower count")
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    print(f"Error extracting follower count: {str(e)}")
                    return 0
                time.sleep(1)

    def _extract_total_likes(self):
        """Extract total likes with retry logic"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                likes_element = self.page.wait_for_selector('strong[data-e2e="likes-count"]', 
                                                          timeout=DEFAULT_TIMEOUT)
                if likes_element:
                    likes_text = likes_element.text_content()
                    count = self._convert_count_to_number(likes_text)
                    if count > 0:
                        return count
                raise Exception("Failed to get valid likes count")
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    print(f"Error extracting total likes: {str(e)}")
                    return 0
                time.sleep(1)

    def _extract_video_data(self, element):
        """Extract data from a single video element with improved reliability"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Extract video link which contains the ID
                link_element = element.query_selector('a[href^="https://www.tiktok.com/"]')
                video_url = link_element.get_attribute('href')
                video_id = video_url.split('/')[-1]
                
                # Extract view count
                views_element = element.query_selector('strong[class*="video-count"]')
                views = self._convert_count_to_number(views_element.text_content()) if views_element else 0
                
                # Need to navigate to video page to get engagement metrics
                video_page = self.context.new_page()
                try:
                    video_page.goto(video_url, timeout=DEFAULT_TIMEOUT)
                    video_page.wait_for_load_state('networkidle')
                    
                    # Wait for engagement metrics to load
                    video_page.wait_for_selector('strong[data-e2e="like-count"]', timeout=DEFAULT_TIMEOUT)
                    
                    # Extract metrics from video page
                    likes = self._extract_likes_from_page(video_page)
                    comments = self._extract_comments_from_page(video_page)
                    shares = self._extract_shares_from_page(video_page)
                    description, hashtags = self._extract_description_and_hashtags_from_page(video_page)
                    
                    # Verify we got valid metrics
                    if likes == 0 and comments == 0 and shares == 0:
                        raise Exception("Failed to get any engagement metrics")
                        
                finally:
                    video_page.close()
                
                # Extract posting time from video ID
                posting_time = self._extract_posting_time(video_id)
                
                metrics = {
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'video_id': video_id,
                    'video_url': video_url,
                    'posting_time': posting_time,
                    'views': views,
                    'likes': likes,
                    'comments': comments,
                    'shares': shares,
                    'description': description,
                    'hashtags': hashtags,
                    'is_new': self._is_new_video(posting_time),
                    'is_pinned': self._is_pinned(element)
                }
                
                return metrics
                
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    print(f"Error extracting video data: {str(e)}")
                    return None
                print(f"Retry {retry_count} for video data extraction")
                time.sleep(2)

    def _extract_likes_from_page(self, page):
        """Extract likes count from video page with explicit wait"""
        try:
            likes_element = page.wait_for_selector('strong[data-e2e="like-count"]', timeout=DEFAULT_TIMEOUT)
            if likes_element:
                likes_text = likes_element.text_content()
                return self._convert_count_to_number(likes_text)
            return 0
        except Exception as e:
            print(f"Error extracting video likes: {str(e)}")
            return 0

    def _extract_comments_from_page(self, page):
        """Extract comments count from video page with explicit wait"""
        try:
            comments_element = page.wait_for_selector('strong[data-e2e="comment-count"]', timeout=DEFAULT_TIMEOUT)
            if comments_element:
                comments_text = comments_element.text_content()
                return self._convert_count_to_number(comments_text)
            return 0
        except Exception as e:
            print(f"Error extracting video comments: {str(e)}")
            return 0
    def _extract_shares_from_page(self, page):
        """Extract shares count with shorter timeout and fallback mechanisms"""
        try:
            # Use a shorter timeout specifically for shares to prevent hanging
            SHARE_TIMEOUT = 5000  # 5 seconds timeout for share extraction
            
            # Try multiple selector patterns
            selectors = [
                'strong[data-e2e="share-count"]',  # Basic selector
                'div[data-e2e="video-share"] strong',  # Nested selector
                '[data-e2e="share-count"]',  # Fallback selector
            ]
            
            for selector in selectors:
                try:
                    # Use shorter timeout and state='attached' instead of 'visible'
                    shares_element = page.wait_for_selector(
                        selector, 
                        timeout=SHARE_TIMEOUT,
                        state='attached'  # Less strict than 'visible'
                    )
                    
                    if shares_element:
                        # Get the text content and clean it
                        shares_text = shares_element.text_content().strip()
                        
                        # Skip if we got the "Share" label instead of a number
                        if shares_text.lower() == 'share':
                            continue
                            
                        # Skip if we got an empty string
                        if not shares_text:
                            continue
                        
                        # Try to find a number in the text
                        import re
                        number_match = re.search(r'[\d.,KkMmBb]+', shares_text)
                        if number_match:
                            shares_text = number_match.group()
                            share_count = self._convert_count_to_number(shares_text)
                            if share_count is not None and share_count >= 0:
                                return share_count
                                
                except Exception as selector_error:
                    logging.debug(f"Selector '{selector}' failed: {str(selector_error)}")
                    continue
            
            # If no selector worked, return 0 without extensive retries
            logging.warning("Share count not found, defaulting to 0")
            return 0
            
        except Exception as e:
            logging.error(f"Error extracting video shares: {str(e)}")
            return 0

    def _convert_count_to_number(self, count_text):
        """Convert count text to number with improved handling"""
        try:
            if not count_text:
                return 0
                
            # Remove any spaces and handle international formatting
            count_text = count_text.replace(' ', '').replace(',', '').strip()
            
            # Skip if we somehow got a non-numeric text
            if count_text.lower() == 'share':
                return 0
                
            # Convert K, M, B suffixes to actual numbers (case insensitive)
            count_text = count_text.upper()
            if 'K' in count_text:
                return float(count_text.replace('K', '')) * 1000
            elif 'M' in count_text:
                return float(count_text.replace('M', '')) * 1000000
            elif 'B' in count_text:
                return float(count_text.replace('B', '')) * 1000000000
            else:
                # Remove any non-numeric characters except decimal points
                cleaned_text = ''.join(c for c in count_text if c.isdigit() or c == '.')
                return float(cleaned_text) if cleaned_text else 0
                
        except (ValueError, AttributeError) as e:
            logging.error(f"Error converting count text '{count_text}': {str(e)}")
            return 0
        
    def _extract_description_and_hashtags_from_page(self, page):
        """Extract description and hashtags with improved reliability"""
        try:
            # Wait for the description container
            desc_container = page.wait_for_selector('[data-e2e="browse-video-desc"]', timeout=DEFAULT_TIMEOUT)
            if not desc_container:
                return "", ""

            # Extract description text
            description = ""
            first_span = desc_container.query_selector('span.css-j2a19r-SpanText')
            if first_span:
                description = first_span.text_content().strip()

            # Extract hashtags using multiple methods
            hashtags = set()
            
            # Method 1: Direct hashtag links
            hashtag_links = desc_container.query_selector_all('a[data-e2e="search-common-link"]')
            
            for link in hashtag_links:
                strong_element = link.query_selector('strong.css-1qkxi8e-StrongText')
                if strong_element:
                    tag_text = strong_element.text_content().strip()
                    if tag_text.startswith('#'):
                        tag = tag_text[1:].strip()
                        if tag:
                            hashtags.add(tag)
                
                # Backup method: extract from href
                href = link.get_attribute('href')
                if href and '/tag/' in href:
                    tag = href.split('/tag/')[-1].strip()
                    if tag:
                        hashtags.add(tag)

            hashtags_list = sorted(list(hashtags))
            return description, ','.join(hashtags_list)
            
        except Exception as e:
            print(f"Error extracting description and hashtags: {str(e)}")
            return "", ""

    def _scroll_and_wait(self, timeout=5000):
        """Scroll down and wait for new content with improved reliability"""
        try:
            last_height = self.page.evaluate('document.documentElement.scrollHeight')
            self.page.evaluate('window.scrollTo(0, document.documentElement.scrollHeight)')
            
            # Wait for new content with multiple checks
            start_time = time.time()
            while time.time() - start_time < timeout/1000:
                new_height = self.page.evaluate('document.documentElement.scrollHeight')
                if new_height > last_height:
                    # Wait a bit more for content to fully load
                    time.sleep(1)
                    return True
                time.sleep(0.1)
            return False
            
        except Exception as e:
            print(f"Error during scroll: {str(e)}")
            return False
        
    def _check_content_loaded(self) -> bool:
        """Check if the main content has loaded successfully"""
        try:
            # Look for key elements that indicate content is loaded
            indicators = [
                'div[data-e2e="user-post-item"]',  # Video items
                'strong[data-e2e="followers-count"]',  # Follower count
                'strong[data-e2e="likes-count"]'  # Likes count
            ]
            
            # Check if at least one indicator is present
            for selector in indicators:
                if self.page.query_selector(selector):
                    return True
            
            # Also check for bot detection or empty content indicators
            bot_detection_signs = [
                'div[class*="verify-bar"]',
                'div[class*="captcha"]',
                'iframe[src*="verify"]'
            ]
            
            for selector in bot_detection_signs:
                if self.page.query_selector(selector):
                    logging.warning("Bot detection elements found")
                    return False
            
            return False
            
        except Exception as e:
            logging.error(f"Error checking content: {str(e)}")
            return False
    def rotate_browser_session(self):
        """Close current browser session and start a new one"""
        logging.info("Rotating browser session...")
        self.cleanup()
        time.sleep(random.uniform(2, 5))  # Wait before starting new session
        self.start_browser()

    def load_page_with_retry(self, url, max_retries=3):
        """Load page with session rotation if content doesn't appear"""
        for attempt in range(max_retries):
            try:
                # Go to the page
                self.page.goto(url, timeout=DEFAULT_TIMEOUT)
                self.page.wait_for_load_state('networkidle')
                
                # Wait a bit and check if content loaded
                time.sleep(random.uniform(2, 4))
                if self._check_content_loaded():
                    return True
                
                logging.warning(f"Content not loaded properly on attempt {attempt + 1}")
                
                if attempt < max_retries - 1:
                    logging.info("Rotating browser session and retrying...")
                    self.rotate_browser_session()
                    continue
                    
            except Exception as e:
                logging.error(f"Error loading page on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    self.rotate_browser_session()
                    continue
                
        return False

    def _save_account_metrics(self, metrics):
        """Save account metrics to CSV with error handling"""
        try:
            file_path = os.path.join(self.account_data_dir, ACCOUNT_METRICS_FILE)
            df = pd.DataFrame([metrics])
            
            # Ensure all timestamps are properly formatted
            timestamp_columns = ['scrape_timestamp']
            for col in timestamp_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
        except Exception as e:
            print(f"Error saving account metrics: {str(e)}")

    def _save_video_metrics(self, videos):
        """Save video metrics to CSV with error handling"""
        try:
            if videos:
                file_path = os.path.join(self.account_data_dir, VIDEO_METRICS_FILE)
                df = pd.DataFrame(videos)
                
                # Ensure all timestamps are properly formatted
                timestamp_columns = ['posting_time', 'scrape_timestamp']
                for col in timestamp_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d %H:%M:%S')
                
                df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
        except Exception as e:
            print(f"Error saving video metrics: {str(e)}")

    def _extract_posting_time(self, video_id):
        """Extract posting time from video ID with error handling"""
        try:
            # TikTok video IDs contain timestamp in the first part
            timestamp = int(video_id) >> 32
            return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(f"Error extracting posting time: {str(e)}")
            return None

    def _is_pinned(self, element):
        """Check if video is pinned with improved reliability"""
        try:
            pinned_element = element.query_selector('div[data-e2e="video-card-badge"]')
            if pinned_element:
                text_content = pinned_element.text_content().lower()
                return "pinned" in text_content
            return False
        except Exception as e:
            print(f"Error checking pinned status: {str(e)}")
            return False

    def _is_new_video(self, posting_time):
        """Check if video is from the last 24 hours with improved validation"""
        if not posting_time:
            return False
        try:
            post_time = datetime.strptime(posting_time, '%Y-%m-%d %H:%M:%S')
            time_diff = datetime.now() - post_time
            return time_diff.total_seconds() <= NEW_VIDEO_THRESHOLD * 3600
        except Exception as e:
            print(f"Error checking if video is new: {str(e)}")
            return False

    def cleanup(self):
        """Close browser and cleanup with error handling"""
        try:
            if hasattr(self, 'page'):
                self.page.close()
            if hasattr(self, 'context'):
                self.context.close()
            if hasattr(self, 'browser'):
                self.browser.close()
            if hasattr(self, 'playwright'):
                self.playwright.stop()
        except Exception as e:
            logging.error(f"Error during cleanup: {str(e)}")