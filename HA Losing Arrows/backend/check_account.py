#!/usr/bin/env python
# US Cash Account Information Display
# Focused version that targets US cash account specifically
# python3 ../purehtc/check_account.py

from moomoo import *
import pandas as pd
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# API Connection Settings
MOOMOOOPEND_ADDRESS = '127.0.0.1'
MOOMOOOPEND_PORT = 11111
TRADING_ENVIRONMENT = TrdEnv.REAL
TRADING_MARKET = TrdMarket.US
TRADING_PWD = '772877'

class MoomooUSAccountInfo:
    def __init__(self):
        self.quote_context = OpenQuoteContext(host=MOOMOOOPEND_ADDRESS, port=MOOMOOOPEND_PORT)
        self.trade_context = OpenSecTradeContext(
            filter_trdmarket=TRADING_MARKET,
            host=MOOMOOOPEND_ADDRESS,
            port=MOOMOOOPEND_PORT,
            security_firm=SecurityFirm.FUTUINC
        )
        self.acc_id = None
        self.trd_env = TRADING_ENVIRONMENT
        
    def connect(self):
        """Establish connection with Moomoo API"""
        logger.info("Connecting to Moomoo API...")
        
        # Unlock trading (required for real account)
        if TRADING_ENVIRONMENT == TrdEnv.REAL:
            for attempt in range(3):
                ret, data = self.trade_context.unlock_trade(TRADING_PWD)
                if ret == RET_OK:
                    logger.info('Trade unlocked successfully!')
                    break
                logger.warning(f'Unlock attempt {attempt+1} failed: {data}')
                time.sleep(1)
                if attempt == 2:
                    logger.error("Failed to unlock trade after 3 attempts")
                    return False
        
        # Get account list
        return self.get_account_list()
    
    def get_account_list(self):
        """Get list of available accounts"""
        print("\n" + "="*80)
        print("📑 ACCOUNT LIST")
        print("="*80)
        
        ret, data = self.trade_context.get_acc_list()
        if ret == RET_OK:
            print(data)
            
            if len(data) > 0 and 'acc_id' in data.columns:
                account_ids = data['acc_id'].values.tolist()
                print(f"Available Account IDs: {account_ids}")
                
                # Use the first account ID by default
                self.acc_id = data['acc_id'][0]
                print(f"Using Account ID: {self.acc_id}")
                
                # Get trading environment for this account
                if 'trd_env' in data.columns:
                    environments = data['trd_env'].values.tolist()
                    print(f"Trading Environments: {environments}")
                    # Use the environment of the selected account
                    self.trd_env = data['trd_env'][0]
                    print(f"Using Trading Environment: {self.trd_env}")
                
                return True
            else:
                logger.error("No account IDs found in response")
        else:
            logger.error(f"get_acc_list error: {data}")
        
        return False
        
    def get_account_info(self):
        """Get basic account information"""
        if self.acc_id is None:
            logger.error("No account ID available")
            return None
            
        ret, acc_info = self.trade_context.accinfo_query(
            trd_env=self.trd_env,
            acc_id=self.acc_id
        )
            
        if ret != RET_OK:
            logger.error(f"Failed to get account info: {acc_info}")
            return None
            
        return acc_info
        
    def get_positions(self):
        """Get current positions"""
        if self.acc_id is None:
            logger.error("No account ID available")
            return None
            
        ret, positions = self.trade_context.position_list_query(
            trd_env=self.trd_env,
            acc_id=self.acc_id
        )
            
        if ret != RET_OK:
            logger.error(f"Failed to get positions: {positions}")
            return None
            
        # Filter only US positions
        if not positions.empty and 'code' in positions.columns:
            us_positions = positions[positions['code'].str.startswith('US.')]
            return us_positions
        return positions
    
    def display_us_account_summary(self):
        """Display US account summary information"""
        # Get account information
        acc_info = self.get_account_info()
        if acc_info is None:
            return
        
        print("\n" + "="*80)
        print("🇺🇸 US CASH ACCOUNT SUMMARY")
        print("="*80)
        
        # Direct display of US account info
        try:
            # Get US cash specific information
            us_cash = acc_info['us_cash'].values[0] if 'us_cash' in acc_info.columns else 'N/A'
            us_withdrawal = acc_info['us_avl_withdrawal_cash'].values[0] if 'us_avl_withdrawal_cash' in acc_info.columns else 'N/A'
            
            print("US Account Information:")
            print(f"  US Cash Balance: ${us_cash:,.2f}")
            print(f"  US Available for Withdrawal: ${us_withdrawal:,.2f}")
            
            # Show additional relevant US metrics
            print("\nAdditional US Trading Information:")
            
            # Pattern Day Trader status
            if 'is_pdt' in acc_info.columns:
                print(f"  PDT Status: {'Yes' if acc_info['is_pdt'].values[0] else 'No'}")
            
            if 'pdt_seq' in acc_info.columns:
                print(f"  PDT Sequence: {acc_info['pdt_seq'].values[0]}")
                
            if 'beginning_dtbp' in acc_info.columns and not pd.isna(acc_info['beginning_dtbp'].values[0]):
                print(f"  Beginning Day Trading Buying Power: ${acc_info['beginning_dtbp'].values[0]:,.2f}")
                
            if 'remaining_dtbp' in acc_info.columns and not pd.isna(acc_info['remaining_dtbp'].values[0]):
                print(f"  Remaining Day Trading Buying Power: ${acc_info['remaining_dtbp'].values[0]:,.2f}")
                
            # Get overall account metrics that impact US trading
            print("\nOverall Account Metrics (Affecting US Trading):")
            if 'cash' in acc_info.columns:
                print(f"  Total Cash: ${acc_info['cash'].values[0]:,.2f}")
                
            if 'market_val' in acc_info.columns:
                print(f"  Total Market Value: ${acc_info['market_val'].values[0]:,.2f}")
            
            if 'total_assets' in acc_info.columns:
                print(f"  Total Assets: ${acc_info['total_assets'].values[0]:,.2f}")
                
        except Exception as e:
            logger.error(f"Error formatting US account summary: {e}")
            print("Raw account info:")
            print(acc_info)
    
    def display_us_positions(self):
        """Display US positions with details"""
        positions = self.get_positions()
        
        if positions is None:
            return
            
        if positions.empty:
            print("\n" + "="*80)
            print("🇺🇸 US POSITIONS (No positions currently)")
            print("="*80)
            return
            
        print("\n" + "="*80)
        print("🇺🇸 US POSITIONS")
        print("="*80)
        
        try:
            # Add calculated cost basis column
            if 'cost_price' in positions.columns and 'qty' in positions.columns:
                positions['cost_basis'] = positions['qty'] * positions['cost_price']
            
            # Format the position information as a clean table
            print("\nUS Position Details:")
            # Extract and organize the most useful columns
            position_data = []
            headers = ["Symbol", "Quantity", "Avg Cost ($)", "Cost Basis ($)", "Side"]
            
            for _, row in positions.iterrows():
                symbol = row['code'].replace('US.', '') if 'code' in row else 'N/A'
                qty = row['qty'] if 'qty' in row else 0
                cost = row['cost_price'] if 'cost_price' in row else 0
                basis = row['cost_basis'] if 'cost_basis' in row else 0
                side = row['position_side'] if 'position_side' in row else 'N/A'
                
                position_data.append([
                    symbol,
                    qty,
                    f"{cost:,.4f}",
                    f"{basis:,.2f}",
                    side
                ])
            
            # Print the table
            self.print_table(headers, position_data)
            
            # Calculate portfolio totals
            if 'cost_price' in positions.columns and 'qty' in positions.columns:
                total_cost_basis = positions['qty'].mul(positions['cost_price']).sum()
                print("\nUS Portfolio Summary:")
                print(f"Total US Cost Basis: ${total_cost_basis:,.2f}")
                print(f"Total US Positions: {len(positions)}")
                print(f"Total US Shares: {positions['qty'].sum()}")
            
        except Exception as e:
            logger.error(f"Error formatting US positions: {e}")
            print("Raw US positions data:")
            print(positions)
    
    def print_table(self, headers, data):
        """Print a simple ASCII table"""
        # Calculate column widths
        widths = [len(header) for header in headers]
        for row in data:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))
        
        # Print header
        header_line = "| "
        for i, header in enumerate(headers):
            header_line += header.ljust(widths[i]) + " | "
        print(header_line)
        
        # Print separator
        separator = "+-" + "-+-".join(["-" * width for width in widths]) + "-+"
        print(separator)
        
        # Print data
        for row in data:
            row_line = "| "
            for i, cell in enumerate(row):
                row_line += str(cell).ljust(widths[i]) + " | "
            print(row_line)
    
    def display_all_info(self):
        """Display all US account information in a clean format"""
        if not self.connect():
            logger.error("Failed to connect to Moomoo API. Exiting.")
            return
            
        try:
            self.display_us_account_summary()
            self.display_us_positions()
        finally:
            # Clean up
            self.quote_context.close()
            self.trade_context.close()
            logger.info("Connection closed")

def main():
    """Main function to run the application"""
    print("\n" + "*"*80)
    print("🚀 MOOMOO US ACCOUNT INFORMATION DISPLAY")
    print("*"*80)
    
    app = MoomooUSAccountInfo()
    app.display_all_info()

if __name__ == "__main__":
    main()
