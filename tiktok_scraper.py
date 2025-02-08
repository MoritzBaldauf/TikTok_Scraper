from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from datetime import datetime, timedelta
import pandas as pd
import logging
import time
import random
import os
from config import *
from browser_setup import BrowserSetup

class TikTokScraper:
    def __init__(self, account_name):
        self.account_name = account_name
        self.account_url = f"https://www.tiktok.com/@{account_name}"
        self.setup_data_directories()
        
    def setup_data_directories(self):
        """Create necessary directories for data storage"""
        self.account_data_dir = os.path.join(DATA_DIR, self.account_name)
        os.makedirs(self.account_data_dir, exist_ok=True)
        logging.info(f"Set up data directory for {self.account_name}")

    def start_browser(self):
        """Initialize browser with human-like characteristics"""
        browser_setup = BrowserSetup()
        self.driver = browser_setup.create_human_browser()
        browser_setup.add_human_behavior(self.driver)
        time.sleep(random.uniform(1, 3))

    def _check_content_loaded(self) -> bool:
        """Check if the main content has loaded successfully"""
        try:
            # Look for key elements that indicate content is loaded
            indicators = [
                'div[data-e2e="user-post-item"]',  # Video items
                'strong[data-e2e="followers-count"]',  # Follower count
                'strong[data-e2e="likes-count"]',  # Likes count
                'h3[data-e2e="user-title"]'  # Username
            ]
            
            found_elements = 0
            for selector in indicators:
                if self.driver.find_elements(By.CSS_SELECTOR, selector):
                    found_elements += 1
            
            # Return true if we found at least 2 indicators
            if found_elements >= 2:
                return True
                
            # Check for bot detection or empty content indicators
            bot_detection_signs = [
                'div[class*="verify-bar"]',
                'div[class*="captcha"]',
                'iframe[src*="verify"]',
                'div[class*="DivVerifyContainer"]'
            ]
            
            for selector in bot_detection_signs:
                if self.driver.find_elements(By.CSS_SELECTOR, selector):
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
                self.driver.get(url)
                time.sleep(random.uniform(2, 4))  # Wait for initial load
                
                # Check if content loaded
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

    def cleanup(self):
        """Close browser and cleanup with error handling"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
        except Exception as e:
            logging.error(f"Error during cleanup: {str(e)}")

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
                video_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-e2e="user-post-item"]')
                
                for element in video_elements:
                    video_id = element.get_attribute('data-video-id')
                    if len(videos) > 0 and any(v['video_id'] == video_id for v in videos):
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
                    
                # Scroll to load more
                self._scroll_and_wait()
            
            self._save_video_metrics(videos)
            return videos
            
        except Exception as e:
            logging.error(f"Error scraping videos: {str(e)}")
            return []

    def _extract_follower_count(self):
        """Extract follower count with retry logic"""
        try:
            follower_element = self.driver.find_element(By.CSS_SELECTOR, 'strong[data-e2e="followers-count"]')
            if follower_element:
                follower_text = follower_element.text
                return self._convert_count_to_number(follower_text)
            return 0
        except Exception as e:
            logging.error(f"Error extracting follower count: {str(e)}")
            return 0

    def _extract_total_likes(self):
        """Extract total likes with retry logic"""
        try:
            likes_element = self.driver.find_element(By.CSS_SELECTOR, 'strong[data-e2e="likes-count"]')
            if likes_element:
                likes_text = likes_element.text
                return self._convert_count_to_number(likes_text)
            return 0
        except Exception as e:
            logging.error(f"Error extracting total likes: {str(e)}")
            return 0

    def _simulate_human_behavior(self):
        """Simulate human-like behavior"""
        try:
            # Random mouse movements
            viewport_width = self.driver.execute_script("return window.innerWidth;")
            viewport_height = self.driver.execute_script("return window.innerHeight;")
            
            for _ in range(random.randint(3, 7)):
                x = random.randint(0, viewport_width)
                y = random.randint(0, viewport_height)
                self.driver.execute_script(f"""
                    const event = new MouseEvent('mousemove', {{
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: {x},
                        clientY: {y}
                    }});
                    document.dispatchEvent(event);
                """)
                time.sleep(random.uniform(0.1, 0.3))
            
            # Random scrolling
            scroll_amount = random.randint(300, 700)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            logging.error(f"Error in human behavior simulation: {str(e)}")

    def _scroll_and_wait(self):
        """Scroll down and wait for new content"""
        try:
            # Get current height
            last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(random.uniform(1, 2))
            
            # Calculate new height
            new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            
            return new_height > last_height
            
        except Exception as e:
            logging.error(f"Error during scroll: {str(e)}")
            return False

    def _extract_video_data(self, element):
        """Extract data from a single video element"""
        try:
            # Extract video URL and ID
            link_element = element.find_element(By.CSS_SELECTOR, 'a[href^="https://www.tiktok.com/"]')
            video_url = link_element.get_attribute('href')
            video_id = video_url.split('/')[-1]
            
            # Extract view count
            views_element = element.find_element(By.CSS_SELECTOR, 'strong[class*="video-count"]')
            views = self._convert_count_to_number(views_element.text) if views_element else 0
            
            # Get video page metrics
            video_metrics = self._get_video_page_metrics(video_url)
            
            # Calculate if video is new based on posting time
            is_new = True  # Default to True if we can't determine
            if video_metrics.get('posting_time'):
                try:
                    posting_time = datetime.strptime(video_metrics['posting_time'], '%Y-%m-%d %H:%M:%S')
                    hours_old = (datetime.now() - posting_time).total_seconds() / 3600
                    is_new = hours_old <= NEW_VIDEO_THRESHOLD
                except Exception as e:
                    logging.warning(f"Error calculating video age: {str(e)}")
            
            # Combine all metrics
            metrics = {
                'video_id': video_id,
                'video_url': video_url,
                'views': views,
                'is_pinned': self._is_pinned(element),
                'is_new': is_new,  # Add this field
                **video_metrics
            }
            
            return metrics
            
        except Exception as e:
            logging.error(f"Error extracting video data: {str(e)}")
            return None
        
    def _get_video_page_metrics(self, video_url):
        """Get metrics from video page"""
        try:
            # Open video in new tab
            self.driver.execute_script(f"window.open('{video_url}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            time.sleep(random.uniform(2, 3))
            
            # Extract metrics
            metrics = {
                'likes': self._extract_metric('strong[data-e2e="like-count"]'),
                'comments': self._extract_metric('strong[data-e2e="comment-count"]'),
                'shares': self._extract_metric('strong[data-e2e="share-count"]'),
                'description': self._extract_description(),
                'hashtags': self._extract_hashtags(),
                'posting_time': self._extract_posting_time()
            }
            
            # Close tab and switch back
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            
            return metrics
            
        except Exception as e:
            logging.error(f"Error getting video page metrics: {str(e)}")
            # Ensure we're back on the main tab
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
            return {
                'likes': 0,
                'comments': 0,
                'shares': 0,
                'description': '',
                'hashtags': '',
                'posting_time': None
            }

    def _extract_metric(self, selector):
        """Extract numeric metric from element"""
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            return self._convert_count_to_number(element.text) if element else 0
        except Exception:
            return 0

    def _extract_description(self):
        """Extract video description"""
        try:
            desc_element = self.driver.find_element(By.CSS_SELECTOR, '[data-e2e="browse-video-desc"]')
            return desc_element.text if desc_element else ""
        except Exception:
            return ""

    def _extract_hashtags(self):
        """Extract hashtags from video"""
        try:
            hashtag_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/tag/"]')
            hashtags = []
            for element in hashtag_elements:
                tag = element.get_attribute('href').split('/tag/')[-1]
                if tag:
                    hashtags.append(tag)
            return ','.join(hashtags)
        except Exception:
            return ""

    def _is_pinned(self, element):
        """Check if video is pinned"""
        try:
            pinned_element = element.find_element(By.CSS_SELECTOR, 'div[data-e2e="video-card-badge"]')
            return "pinned" in pinned_element.text.lower() if pinned_element else False
        except Exception:
            return False

    def _convert_count_to_number(self, count_text):
        """Convert count text to number"""
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

    def _extract_posting_time(self):
        """Extract posting time from video page"""
        try:
            # Try multiple possible selectors for time element
            selectors = [
                'span[data-e2e="browser-nickname"] + span',
                'span[data-e2e="video-meta-time"]',
                'span.time-tag',  # Add more potential selectors
                '[data-e2e="browser-nickname"]~span'
            ]
            
            for selector in selectors:
                try:
                    time_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if time_element and time_element.text:
                        return self._parse_time_text(time_element.text)
                except Exception:
                    continue
                    
            # If no selector works, try finding by text pattern
            spans = self.driver.find_elements(By.TAG_NAME, 'span')
            for span in spans:
                text = span.text
                if any(pattern in text.lower() for pattern in ['ago', 'hours', 'days', 'weeks']):
                    return self._parse_time_text(text)
                    
            return None
        except Exception as e:
            logging.error(f"Error extracting posting time: {str(e)}")
            return None
        
        
    def _parse_time_text(self, time_text):
        """Parse TikTok's relative time text into datetime"""
        try:
            current_time = datetime.now()
            
            if 'h' in time_text:  # hours ago
                hours = int(time_text.replace('h', ''))
                return (current_time - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
            elif 'd' in time_text:  # days ago
                days = int(time_text.replace('d', ''))
                return (current_time - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            elif 'w' in time_text:  # weeks ago
                weeks = int(time_text.replace('w', ''))
                return (current_time - timedelta(weeks=weeks)).strftime('%Y-%m-%d %H:%M:%S')
            elif 'm' in time_text:  # minutes ago
                minutes = int(time_text.replace('m', ''))
                return (current_time - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                # Try to parse as exact date
                return datetime.strptime(time_text, '%Y-%m-%d').strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logging.error(f"Error parsing time text '{time_text}': {str(e)}")
            return None

    def _save_account_metrics(self, metrics):
        """Save account metrics to CSV"""
        try:
            file_path = os.path.join(self.account_data_dir, ACCOUNT_METRICS_FILE)
            df = pd.DataFrame([metrics])
            
            # Ensure all timestamps are properly formatted
            timestamp_columns = ['scrape_timestamp']
            for col in timestamp_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
            logging.info(f"Saved account metrics for {self.account_name}")
        except Exception as e:
            logging.error(f"Error saving account metrics: {str(e)}")

    def _save_video_metrics(self, videos):
        """Save video metrics to CSV"""
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
                logging.info(f"Saved {len(videos)} video metrics for {self.account_name}")
        except Exception as e:
            logging.error(f"Error saving video metrics: {str(e)}")