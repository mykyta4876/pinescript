import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains  # Added this import
from selenium.webdriver.common.keys import Keys
import time
from datetime import datetime
import json

class TradingViewAutomation:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.driver = None
        
    def setup_driver(self):
        """Initialize Chrome driver with undetected-chromedriver"""
        options = uc.ChromeOptions()
        # options.add_argument('--headless')  # Run in headless mode
        self.driver = uc.Chrome(options=options)
        
    def login(self):
        """Login to TradingView"""
        try:
            self.driver.get('https://www.tradingview.com/#signin')
            
            # actions = ActionChains(self.driver)
            # actions.send_keys(Keys.ESCAPE)
            # actions.perform()
            
            # clearfix_button = self.driver.find_element(By.CLASS_NAME, "i-clearfix")
            # clearfix_button.click()
            
            email_button = self.driver.find_element(By.NAME, "Email")
            email_button.click()
            
            # Wait for email input and enter username
            email_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "id_username"))
            )
            email_input.send_keys(self.username)
            
            # Find and enter password
            password_input = self.driver.find_element(By.NAME, "id_password")
            password_input.send_keys(self.password)
            
            # Click sign in button
            sign_in_button = self.driver.find_element(By.XPATH, "//button[@data-overflow-tooltip-text='Sign in']")
            sign_in_button.click()
            
            print("Successfully logged in")
            return True
            
        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False
            
    def add_to_watchlist(self, symbols):
        """Add symbols to watchlist"""
        try:
            # For each symbol
            for symbol in symbols:
                # Click add symbol button
                watchlist_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Watchlist, details and news']"))
                )
                watchlist_button.click()
                
                # Click add symbol button
                add_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Add symbol']"))
                )
                add_button.click()
                
                # Enter symbol
                symbol_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "tv-search-row__input"))
                )
                symbol_input.send_keys(symbol)
                
                # Wait and click first result
                first_result = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "tv-search-row__result"))
                )
                first_result.click()
                
                time.sleep(1)  # Wait between symbols
                
            print(f"Successfully added symbols: {symbols}")
            return True
            
        except Exception as e:
            print(f"Failed to add symbols: {str(e)}")
            return False
            
    def generate_option_symbols(self):
        """Generate option symbols for QQQ"""
        try:
            # Get QQQ price
            self.driver.get('https://www.tradingview.com/symbols/NASDAQ-QQQ/')
            time.sleep(3)
            
            price_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "tv-symbol-price-quote__value"))
            )
            qqq_price = float(price_element.text)
            
            # Calculate strikes
            put_strike = round((qqq_price + 2) * 2) / 2
            call_strike = round((qqq_price - 2) * 2) / 2
            
            # Generate date string (YYMMDD)
            next_date = datetime.now()
            date_str = next_date.strftime("%y%m%d")
            
            # Generate symbols
            symbols = [
                f"OPRA:QQQ{date_str}P{put_strike}",
                f"OPRA:QQQ{date_str}C{call_strike}"
            ]
            
            return symbols
            
        except Exception as e:
            print(f"Failed to generate symbols: {str(e)}")
            return []
            
    def cleanup(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()

def main():
    # Initialize automation with your credentials
    tv = TradingViewAutomation(
        username="jamisonkennethwayneii",
        password="4esz%RDX^TFC"
    )
    
    try:
        # Setup driver
        tv.setup_driver()
        
        # Login
        if not tv.login():
            print("Failed to login, exiting...")
            return
            
        while True:
            now = datetime.now()
            
            # Check if it's 8 AM
            if now.hour == 8 and now.minute == 0:
                # Generate new symbols
                symbols = tv.generate_option_symbols()
                
                if symbols:
                    # Add to watchlist
                    tv.add_to_watchlist(symbols)
                    
            # Sleep for 60 seconds before next check
            time.sleep(60)
                
    except KeyboardInterrupt:
        print("Stopping automation...")
    finally:
        tv.cleanup()

if __name__ == "__main__":
    main()