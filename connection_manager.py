import time
import random
import logging

class ConnectionManager:
    def __init__(self, max_retries=3, base_delay=5):
        self.max_retries = max_retries
        self.base_delay = base_delay

    def execute_with_retry(self, func, *args, **kwargs):
        """Execute a function with exponential backoff retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if "Connection refused" in str(e) or "invalid session id" in str(e):
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logging.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
                    logging.info(f"Waiting {delay:.2f} seconds before retry")
                    time.sleep(delay)
                else:
                    raise
                    
        raise last_exception
    
    def load_page_with_retry(self, url, max_retries=3):
        """Load page with connection retry logic"""
        conn_manager = ConnectionManager(max_retries=max_retries)
        
        def _load_attempt():
            self.driver.get(url)
            time.sleep(random.uniform(2, 4))
            
            if self._check_content_loaded():
                return True
            return False
        
        try:
            return conn_manager.execute_with_retry(_load_attempt)
        except Exception as e:
            logging.error(f"Failed to load page after {max_retries} attempts: {str(e)}")
            return False