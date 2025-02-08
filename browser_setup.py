from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium_stealth import stealth
import random
import json
import os

class BrowserSetup:
    @staticmethod
    def create_human_browser():
        """Create a Selenium browser with human-like characteristics"""
        chrome_options = Options()
        
        # Define user agents pool
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        # Add arguments to make browser more human-like
        chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        chrome_options.add_argument('--disable-blink-features')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--enable-javascript')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Add experimental options
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        # Create preferences including geolocation, notifications, etc.
        prefs = {
            "profile.default_content_setting_values.geolocation": 2,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.media_stream_mic": 2,
            "profile.default_content_setting_values.media_stream_camera": 2,
            "profile.default_content_setting_values.javascript": 1,
            "profile.cookie_controls_mode": 0,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Initialize the browser
        driver = webdriver.Chrome(options=chrome_options)
        
        # Apply stealth settings
        stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            run_on_insecure_origins=False
        )
        
        # Set CDP (Chrome DevTools Protocol) commands
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": random.choice(user_agents),
            "platform": "Windows",
            "acceptLanguage": "en-US,en;q=0.9"
        })
        
        # Modify navigator properties
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        return driver

    @staticmethod
    def add_human_behavior(driver):
        """Add scripts for human-like behavior"""
        # Add random mouse movements
        driver.execute_script("""
            function simulateMouseMovement() {
                const points = [];
                const numPoints = Math.floor(Math.random() * 10) + 5;
                
                for (let i = 0; i < numPoints; i++) {
                    points.push({
                        x: Math.random() * window.innerWidth,
                        y: Math.random() * window.innerHeight
                    });
                }
                
                points.forEach((point, index) => {
                    setTimeout(() => {
                        const event = new MouseEvent('mousemove', {
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            clientX: point.x,
                            clientY: point.y
                        });
                        document.dispatchEvent(event);
                    }, index * (Math.random() * 200 + 100));
                });
            }
            
            // Call periodically
            setInterval(simulateMouseMovement, 3000);
        """)
        
        # Add random scrolling behavior
        driver.execute_script("""
            function simulateScrolling() {
                const maxScroll = Math.max(
                    document.documentElement.scrollHeight,
                    document.body.scrollHeight
                );
                const scrollAmount = Math.random() * 500;
                const currentScroll = window.pageYOffset;
                
                window.scrollTo({
                    top: Math.min(currentScroll + scrollAmount, maxScroll),
                    behavior: 'smooth'
                });
            }
            
            // Call periodically
            setInterval(simulateScrolling, 5000);
        """)

    @staticmethod
    def set_cookies(driver, cookies_file=None):
        """Set cookies from file or default set"""
        try:
            if cookies_file and os.path.exists(cookies_file):
                with open(cookies_file, 'r') as f:
                    cookies = json.load(f)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            else:
                # Set some default cookies
                default_cookies = [
                    {'name': 'language', 'value': 'en'},
                    {'name': 'timezone', 'value': 'UTC'},
                    {'name': 'theme', 'value': 'light'}
                ]
                for cookie in default_cookies:
                    driver.add_cookie(cookie)
        except Exception as e:
            print(f"Error setting cookies: {str(e)}")

# Usage example:
def create_human_like_browser(cookies_file=None):
    """Create and configure a human-like browser instance"""
    browser_setup = BrowserSetup()
    driver = browser_setup.create_human_browser()
    browser_setup.add_human_behavior(driver)
    browser_setup.set_cookies(driver, cookies_file)
    return driver