import requests
import json
from datetime import datetime, timedelta
import time

class TradingViewWatchlistManager:
    def __init__(self, username, password):
        self.session = requests.Session()
        self.base_url = "https://www.tradingview.com"
        self.username = username
        self.password = password
        self.token = None
        
    def login(self):
        """Login to TradingView and get authentication token"""
        login_url = f"{self.base_url}/accounts/signin/"
        data = {
            "username": self.username,
            "password": self.password,
            "remember": "on"
        }
        try:
            response = self.session.post(login_url, data=data)
            if response.status_code == 200:
                self.token = response.cookies.get("sessionid")
                return True
            return False
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False

    def get_watchlist_symbols(self):
        """Get current watchlist symbols"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/watchlists/",
                headers=headers
            )
            return response.json()
        except Exception as e:
            print(f"Error getting watchlist: {str(e)}")
            return None

    def update_watchlist(self, symbols):
        """Update watchlist with new symbols"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        data = {
            "symbols": symbols
        }
        try:
            response = self.session.put(
                f"{self.base_url}/api/v1/watchlists/default/",
                headers=headers,
                json=data
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error updating watchlist: {str(e)}")
            return False

    def generate_option_symbols(self):
        """Generate option symbols based on current QQQ price"""
        # This is a placeholder - you'll need to implement actual price fetching
        qqq_price = 400  # Example price
        
        # Calculate strike prices
        put_strike = round((qqq_price + 2) * 2) / 2
        call_strike = round((qqq_price - 2) * 2) / 2
        
        # Get next trading day
        next_date = datetime.now() + timedelta(days=1)
        date_str = next_date.strftime("%y%m%d")
        
        # Generate symbols
        symbols = [
            f"OPRA:QQQ{date_str}P{put_strike}",
            f"OPRA:QQQ{date_str}C{call_strike}"
        ]
        return symbols

def main():
    # Initialize manager
    manager = TradingViewWatchlistManager(
        username="jamisonkennethwayneii",
        password="4esz%RDX^TFC"
    )
    
    # Login
    if not manager.login():
        print("Failed to login")
        return
    
    while True:
        now = datetime.now()
        
        # Check if it's 8 AM
        if now.hour == 8 and now.minute == 0:
            # Generate new symbols
            new_symbols = manager.generate_option_symbols()
            
            # Update watchlist
            if manager.update_watchlist(new_symbols):
                print(f"Successfully updated watchlist with symbols: {new_symbols}")
            else:
                print("Failed to update watchlist")
        
        # Sleep for 60 seconds before next check
        time.sleep(60)

if __name__ == "__main__":
    main()