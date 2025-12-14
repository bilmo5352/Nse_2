"""
Dashboard scraper for NSE equity quotes.
Opens NSE homepage, searches for a symbol, selects first suggestion, and scrapes all equity quote data.
"""

import asyncio
import os
import random
import json
import re
import argparse
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from browser_utils import get_browser_launch_args


async def human_delay(min_sec: float = 0.5, max_sec: float = 2.0):
    """Add random delay to simulate human behavior."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


def extract_value_after_label(text: str, label: str) -> str:
    """
    Extract numeric value that appears immediately after a label in text.
    Example: "Open1,534.00" with label "Open" returns "1,534.00"
    """
    pattern = label + r'([0-9,.\-]+)'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None


def parse_nse_quote_html(html_content: str) -> dict:
    """
    Parse the rendered NSE equity quote HTML and extract all data.
    
    NSE stores data in specific div structures with continuous text
    (no spaces between labels and values).
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {}
    
    try:
        # Get main body text for pattern matching
        main_body = soup.find('main', id='midBody')
        if not main_body:
            return {"error": "Main body not found"}
        
        body_text = main_body.get_text()
        
        # Extract symbol from header
        symbol_elem = soup.find('span', class_='symbol-text')
        if symbol_elem:
            data['symbol'] = symbol_elem.get_text(strip=True)
        
        # Extract current price from index-highlight
        ltp_div = soup.find('div', class_='index-highlight')
        if ltp_div:
            spans = ltp_div.find_all('span', class_='value')
            if not spans:
                spans = ltp_div.find_all('span')
            price_text = ''.join([span.get_text(strip=True) for span in spans])
            data['last_price'] = price_text.strip()
        
        # Extract change and percent change
        change_divs = soup.find_all('div', class_='index-change-highlight')
        if len(change_divs) >= 2:
            change_spans = change_divs[0].find_all('span')
            pct_spans = change_divs[1].find_all('span')
            data['change'] = ''.join([s.get_text(strip=True) for s in change_spans]).strip()
            data['percent_change'] = ''.join([s.get_text(strip=True) for s in pct_spans]).strip()
        
        # Extract OHLC and VWAP from symbol-item divs
        symbol_items = soup.find_all('div', class_='symbol-item')
        for item in symbol_items:
            text = item.get_text(strip=True)
            
            if text.startswith('Prev. Close'):
                data['prev_close'] = extract_value_after_label(text, 'Prev. Close')
            elif text.startswith('Open'):
                data['open'] = extract_value_after_label(text, 'Open')
            elif text.startswith('High'):
                data['high'] = extract_value_after_label(text, 'High')
            elif text.startswith('Low'):
                data['low'] = extract_value_after_label(text, 'Low')
            elif text.startswith('VWAP'):
                data['vwap'] = extract_value_after_label(text, 'VWAP')
            elif text.startswith('Close'):
                close_val = extract_value_after_label(text, 'Close')
                if close_val and close_val != '-':
                    data['close'] = close_val
        
        # Extract volume and value from body text
        vol_match = re.search(r'Traded Volume \(Lakhs\)([0-9,.]+)', body_text)
        if vol_match:
            data['traded_volume_lakhs'] = vol_match.group(1)
        
        val_match = re.search(r'Traded Value \(₹ Cr\.\)([0-9,.]+)', body_text)
        if val_match:
            data['traded_value_cr'] = val_match.group(1)
        
        # Extract market cap
        mcap_match = re.search(r'Total Market Cap \(₹ Cr\.\)([0-9,.]+)', body_text)
        if mcap_match:
            data['total_market_cap_cr'] = mcap_match.group(1)
        
        ffmc_match = re.search(r'Free Float Market Cap \(₹ Cr\.\)([0-9,.]+)', body_text)
        if ffmc_match:
            data['free_float_market_cap_cr'] = ffmc_match.group(1)
        
        # Extract impact cost and face value
        impact_match = re.search(r'Impact cost([0-9,.]+)', body_text)
        if impact_match:
            data['impact_cost'] = impact_match.group(1)
        
        fv_match = re.search(r'Face Value([0-9,.]+)', body_text)
        if fv_match:
            data['face_value'] = fv_match.group(1)
        
        # Extract 52-week high and low
        high52_match = re.search(r'52 Week High \([^)]+\)([0-9,.]+)', body_text)
        if high52_match:
            data['52_week_high'] = high52_match.group(1)
        
        low52_match = re.search(r'52 Week Low \([^)]+\)([0-9,.]+)', body_text)
        if low52_match:
            data['52_week_low'] = low52_match.group(1)
        
        # Extract upper and lower bands
        upper_match = re.search(r'Upper Band([0-9,.]+)', body_text)
        if upper_match:
            data['upper_band'] = upper_match.group(1)
        
        lower_match = re.search(r'Lower Band([0-9,.]+)', body_text)
        if lower_match:
            data['lower_band'] = lower_match.group(1)
        
        # Extract delivery data
        del_qty_match = re.search(r'Deliverable / Traded Quantity([0-9,.]+)%', body_text)
        if del_qty_match:
            data['delivery_qty_pct'] = del_qty_match.group(1) + '%'
        
        # Extract volatility
        daily_vol_match = re.search(r'Daily Volatility([0-9,.]+)', body_text)
        if daily_vol_match:
            data['daily_volatility'] = daily_vol_match.group(1)
        
        annual_vol_match = re.search(r'Annualised Volatility([0-9,.]+)', body_text)
        if annual_vol_match:
            data['annualised_volatility'] = annual_vol_match.group(1)
        
        # Extract P/E and other ratios
        pe_match = re.search(r'Symbol P/E([0-9,.]+)', body_text)
        if pe_match:
            data['pe'] = pe_match.group(1)
        
        adj_pe_match = re.search(r'Adjusted P/E([0-9,.]+)', body_text)
        if adj_pe_match:
            data['adjusted_pe'] = adj_pe_match.group(1)
        
        # Extract security info
        isin_match = re.search(r'\(([A-Z]{2}[A-Z0-9]{10})\)', body_text)
        if isin_match:
            data['isin'] = isin_match.group(1)
        
        listing_match = re.search(r'Date of Listing([0-9]{2}-[A-Za-z]{3}-[0-9]{4})', body_text)
        if listing_match:
            data['listing_date'] = listing_match.group(1)
        
        # Extract industry
        industry_match = re.search(r'Basic Industry([A-Za-z &]+)Dashboard', body_text)
        if industry_match:
            data['industry'] = industry_match.group(1).strip()
        
        # Extract order book table data (Qty, Bid (₹), Ask (₹), Qty)
        data['order_book'] = []
        
        # Approach -1: Look for the specific NSE order book structure in OrderData div
        # Structure: <div class="OrderData"><span class="order-book-label">Order Book</span><table class="table">...
        order_table = None
        
        # First, try to find the OrderData div
        order_data_div = soup.find('div', class_='OrderData')
        if order_data_div:
            # Find the table inside OrderData div
            order_table = order_data_div.find('table', class_='table')
            if order_table:
                print("[DEBUG] Found order book table in OrderData div")
        
        # Approach -2: Look for span with class "order-book-label" and find adjacent table
        if not order_table:
            order_book_label = soup.find('span', class_='order-book-label')
            if order_book_label:
                # Find the following table with class "table" - could be sibling or in parent
                # Try next sibling
                next_elem = order_book_label.find_next_sibling()
                while next_elem:
                    if hasattr(next_elem, 'name') and next_elem.name == 'table' and 'table' in next_elem.get('class', []):
                        order_table = next_elem
                        break
                    next_elem = next_elem.find_next_sibling() if hasattr(next_elem, 'find_next_sibling') else None
                
                # If not found as sibling, look in parent
                if not order_table:
                    parent = order_book_label.find_parent()
                    if parent:
                        order_table = parent.find('table', class_='table')
                
                # If still not found, use find_next
                if not order_table:
                    order_table = order_book_label.find_next('table', class_='table')
        
        # Approach -3: Direct search for table with class "table" and specific header structure
        if not order_table:
            tables = soup.find_all('table', class_='table')
            for table in tables:
                thead = table.find('thead')
                if thead:
                    header_row = thead.find('tr')
                    if header_row:
                        headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
                        # Check if headers match: Qty, Bid (₹), Ask (₹), Qty
                        if (len(headers) >= 4 and 
                            'Qty' in headers[0] and 
                            'Bid' in headers[1] and 
                            'Ask' in headers[2] and 
                            'Qty' in headers[3]):
                            order_table = table
                            break
        
        # Extract data from the found order book table
        # IMPORTANT: Include all rows, even if they contain "-" values (as requested by user)
        if order_table:
            tbody = order_table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                print(f"[DEBUG] Found {len(rows)} rows in order book table")
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        # Extract based on structure: Qty (bid), Bid (₹), Ask (₹), Qty (ask)
                        bid_qty = cells[0].get_text(strip=True)
                        bid_price = cells[1].get_text(strip=True)
                        ask_price = cells[2].get_text(strip=True)
                        ask_qty = cells[3].get_text(strip=True)
                        
                        # Create order entry - include ALL values, even if "-" (as user requested)
                        order_entry = {
                            'bid_qty': bid_qty if bid_qty else '-',
                            'bid_price': bid_price if bid_price else '-',
                            'ask_price': ask_price if ask_price else '-',
                            'ask_qty': ask_qty if ask_qty else '-'
                        }
                        
                        # Always add the entry, even if all values are "-"
                        data['order_book'].append(order_entry)
        
        # Approach 0: Most aggressive - look for ANY table with 4+ columns that might be order book
        # This handles cases where headers might not contain "Bid"/"Ask" text
        all_tables = soup.find_all('table')
        for table in all_tables:
            rows = table.find_all('tr')
            if len(rows) >= 3:  # At least header + 2 data rows
                # Check if rows have 4 columns
                sample_row = rows[1] if len(rows) > 1 else rows[0]
                cells = sample_row.find_all(['td', 'th'])
                if len(cells) >= 4:
                    # Try to extract first few rows and validate pattern
                    valid_rows = []
                    for row in rows[1:6]:  # Check first 5 data rows
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 4:
                            cell_texts = [c.get_text(strip=True) for c in cells[:4]]
                            # Pattern validation: Qty (digits), Price (decimal), Price (decimal), Qty (digits)
                            if (cell_texts[0].replace(',', '').replace('-', '').isdigit() and
                                ('.' in cell_texts[1] or ',' in cell_texts[1] or cell_texts[1].replace(',', '').replace('-', '').isdigit()) and
                                ('.' in cell_texts[2] or ',' in cell_texts[2] or cell_texts[2].replace(',', '').replace('-', '').isdigit()) and
                                cell_texts[3].replace(',', '').replace('-', '').isdigit()):
                                valid_rows.append(cell_texts)
                    
                    # If we found at least 2 valid rows matching the pattern, it's likely the order book
                    if len(valid_rows) >= 2:
                        for cell_texts in valid_rows:
                            order_entry = {
                                'bid_qty': cell_texts[0] if cell_texts[0] != '-' else None,
                                'bid_price': cell_texts[1] if cell_texts[1] != '-' else None,
                                'ask_price': cell_texts[2] if cell_texts[2] != '-' else None,
                                'ask_qty': cell_texts[3] if cell_texts[3] != '-' else None
                            }
                            order_entry = {k: v for k, v in order_entry.items() if v is not None}
                            if len(order_entry) >= 2:
                                data['order_book'].append(order_entry)
                        
                        if data['order_book']:
                            break  # Found order book, stop searching
        
        # Approach 1: Look for tables with order book structure (with Bid/Ask headers)
        # First, find all tables in the main body
        if not data['order_book']:
            tables = main_body.find_all('table') if main_body else soup.find_all('table')
        
        for table in tables:
            table_text = table.get_text()
            # Check if this looks like an order book table
            has_bid = 'Bid' in table_text or 'bid' in table_text
            has_ask = 'Ask' in table_text or 'ask' in table_text
            has_qty = 'Qty' in table_text or 'qty' in table_text
            
            if has_bid and has_ask and has_qty:
                rows = table.find_all('tr')
                if len(rows) > 1:
                    # Extract header row
                    header_row = rows[0]
                    header_cells = header_row.find_all(['th', 'td'])
                    headers = [cell.get_text(strip=True) for cell in header_cells]
                    
                    # Find column indices - be flexible with matching
                    qty_idx = None
                    bid_idx = None
                    ask_idx = None
                    ask_qty_idx = None
                    
                    for i, header in enumerate(headers):
                        header_upper = header.upper().replace('₹', '').replace('(', '').replace(')', '').strip()
                        if 'QTY' in header_upper and qty_idx is None:
                            qty_idx = i
                        elif 'BID' in header_upper:
                            bid_idx = i
                        elif 'ASK' in header_upper:
                            ask_idx = i
                        elif 'QTY' in header_upper and qty_idx is not None:
                            ask_qty_idx = i
                    
                    # If we found headers but not all indices, try positional matching
                    # Common pattern: Qty | Bid (₹) | Ask (₹) | Qty
                    if bid_idx is None and ask_idx is None and len(headers) >= 4:
                        # Assume standard order: Qty, Bid, Ask, Qty
                        if qty_idx is None:
                            qty_idx = 0
                        if bid_idx is None:
                            bid_idx = 1
                        if ask_idx is None:
                            ask_idx = 2
                        if ask_qty_idx is None:
                            ask_qty_idx = 3
                    
                    # Extract data rows
                    for row in rows[1:]:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 4:
                            order_entry = {}
                            
                            # Extract based on found indices or positional
                            if qty_idx is not None and qty_idx < len(cells):
                                bid_qty = cells[qty_idx].get_text(strip=True)
                                if bid_qty and (bid_qty.replace(',', '').replace('-', '').isdigit() or bid_qty == '-'):
                                    order_entry['bid_qty'] = bid_qty if bid_qty != '-' else None
                            
                            if bid_idx is not None and bid_idx < len(cells):
                                bid_price = cells[bid_idx].get_text(strip=True)
                                if bid_price and ('.' in bid_price or ',' in bid_price or bid_price == '-'):
                                    order_entry['bid_price'] = bid_price if bid_price != '-' else None
                            
                            if ask_idx is not None and ask_idx < len(cells):
                                ask_price = cells[ask_idx].get_text(strip=True)
                                if ask_price and ('.' in ask_price or ',' in ask_price or ask_price == '-'):
                                    order_entry['ask_price'] = ask_price if ask_price != '-' else None
                            
                            if ask_qty_idx is not None and ask_qty_idx < len(cells):
                                ask_qty = cells[ask_qty_idx].get_text(strip=True)
                                if ask_qty and (ask_qty.replace(',', '').replace('-', '').isdigit() or ask_qty == '-'):
                                    order_entry['ask_qty'] = ask_qty if ask_qty != '-' else None
                            
                            # If we didn't find indices, try positional extraction
                            if not order_entry and len(cells) >= 4:
                                # Try pattern: Qty Bid Ask Qty
                                cell_texts = [c.get_text(strip=True) for c in cells[:4]]
                                # Validate: first and last should be quantities, middle two should be prices
                                if (cell_texts[0].replace(',', '').replace('-', '').isdigit() and
                                    ('.' in cell_texts[1] or ',' in cell_texts[1]) and
                                    ('.' in cell_texts[2] or ',' in cell_texts[2]) and
                                    cell_texts[3].replace(',', '').replace('-', '').isdigit()):
                                    order_entry = {
                                        'bid_qty': cell_texts[0] if cell_texts[0] != '-' else None,
                                        'bid_price': cell_texts[1] if cell_texts[1] != '-' else None,
                                        'ask_price': cell_texts[2] if cell_texts[2] != '-' else None,
                                        'ask_qty': cell_texts[3] if cell_texts[3] != '-' else None
                                    }
                            
                            # Clean None values and add if we have data
                            order_entry = {k: v for k, v in order_entry.items() if v is not None}
                            if len(order_entry) >= 2:  # At least 2 fields
                                data['order_book'].append(order_entry)
                    
                    if data['order_book']:
                        break  # Found order book, stop searching
        
        # Approach 2: Look for divs with specific order book classes/IDs
        if not data['order_book']:
            # Search for divs with order book related attributes
            order_selectors = [
                {'class': lambda x: x and 'order' in str(x).lower()},
                {'id': lambda x: x and ('order' in str(x).lower() or 'bid' in str(x).lower() or 'ask' in str(x).lower())},
                {'class': lambda x: x and 'bid' in str(x).lower()},
                {'class': lambda x: x and 'ask' in str(x).lower()},
            ]
            
            for selector in order_selectors:
                divs = soup.find_all('div', selector)
                for div in divs:
                    div_text = div.get_text()
                    if 'Bid' in div_text and 'Ask' in div_text and 'Qty' in div_text:
                        # Look for table inside this div
                        inner_table = div.find('table')
                        if inner_table:
                            rows = inner_table.find_all('tr')
                            if len(rows) > 1:
                                # Use same extraction logic as Approach 1
                                header_row = rows[0]
                                header_cells = header_row.find_all(['th', 'td'])
                                headers = [cell.get_text(strip=True) for cell in header_cells]
                                
                                # Find indices
                                qty_idx, bid_idx, ask_idx, ask_qty_idx = 0, 1, 2, 3
                                for i, header in enumerate(headers):
                                    header_upper = header.upper().replace('₹', '').replace('(', '').replace(')', '').strip()
                                    if 'QTY' in header_upper and qty_idx is None:
                                        qty_idx = i
                                    elif 'BID' in header_upper:
                                        bid_idx = i
                                    elif 'ASK' in header_upper:
                                        ask_idx = i
                                    elif 'QTY' in header_upper and qty_idx is not None:
                                        ask_qty_idx = i
                                
                                # Extract rows
                                for row in rows[1:]:
                                    cells = row.find_all(['td', 'th'])
                                    if len(cells) >= 4:
                                        order_entry = {}
                                        if qty_idx < len(cells):
                                            bid_qty = cells[qty_idx].get_text(strip=True)
                                            if bid_qty and bid_qty.replace(',', '').replace('-', '').isdigit():
                                                order_entry['bid_qty'] = bid_qty
                                        if bid_idx < len(cells):
                                            bid_price = cells[bid_idx].get_text(strip=True)
                                            if bid_price and ('.' in bid_price or ',' in bid_price):
                                                order_entry['bid_price'] = bid_price
                                        if ask_idx < len(cells):
                                            ask_price = cells[ask_idx].get_text(strip=True)
                                            if ask_price and ('.' in ask_price or ',' in ask_price):
                                                order_entry['ask_price'] = ask_price
                                        if ask_qty_idx < len(cells):
                                            ask_qty = cells[ask_qty_idx].get_text(strip=True)
                                            if ask_qty and ask_qty.replace(',', '').replace('-', '').isdigit():
                                                order_entry['ask_qty'] = ask_qty
                                        
                                        if len(order_entry) >= 2:
                                            data['order_book'].append(order_entry)
                                
                                if data['order_book']:
                                    break
                
                if data['order_book']:
                    break
        
        # Approach 3: Search for tbody elements with order book data
        if not data['order_book']:
            tbodies = soup.find_all('tbody')
            for tbody in tbodies:
                tbody_text = tbody.get_text()
                if 'Bid' in tbody_text and 'Ask' in tbody_text:
                    rows = tbody.find_all('tr')
                    if len(rows) > 0:
                        # Check first row to understand structure
                        first_row = rows[0]
                        cells = first_row.find_all(['td', 'th'])
                        if len(cells) >= 4:
                            # Try to extract all rows
                            for row in rows:
                                cells = row.find_all(['td', 'th'])
                                if len(cells) >= 4:
                                    cell_texts = [c.get_text(strip=True) for c in cells[:4]]
                                    # Validate pattern: Qty (digits), Price (decimal), Price (decimal), Qty (digits)
                                    if (cell_texts[0].replace(',', '').replace('-', '').isdigit() and
                                        ('.' in cell_texts[1] or ',' in cell_texts[1] or cell_texts[1] == '-') and
                                        ('.' in cell_texts[2] or ',' in cell_texts[2] or cell_texts[2] == '-') and
                                        cell_texts[3].replace(',', '').replace('-', '').isdigit()):
                                        order_entry = {
                                            'bid_qty': cell_texts[0] if cell_texts[0] != '-' else None,
                                            'bid_price': cell_texts[1] if cell_texts[1] != '-' else None,
                                            'ask_price': cell_texts[2] if cell_texts[2] != '-' else None,
                                            'ask_qty': cell_texts[3] if cell_texts[3] != '-' else None
                                        }
                                        order_entry = {k: v for k, v in order_entry.items() if v is not None}
                                        if len(order_entry) >= 2:
                                            data['order_book'].append(order_entry)
                            
                            if data['order_book']:
                                break
        
        # Approach 4: Search in main body text for order book pattern (regex-based)
        if not data['order_book']:
            # Look for pattern: "Qty" followed by "Bid" followed by "Ask" followed by "Qty"
            # Then extract following numeric rows
            pattern = r'(?:Qty|qty).*?(?:Bid|bid).*?(?:Ask|ask).*?(?:Qty|qty)'
            match = re.search(pattern, body_text, re.IGNORECASE)
            if match:
                start_pos = match.end()
                # Look for rows of 4 numbers in the next 3000 characters
                section_text = body_text[start_pos:start_pos+3000]
                # Pattern: 4 numbers separated by whitespace (allowing commas and decimals)
                rows_pattern = r'([0-9,]+)\s+([0-9,.]+)\s+([0-9,.]+)\s+([0-9,]+)'
                matches = re.findall(rows_pattern, section_text)
                for match_tuple in matches[:20]:  # Limit to 20 rows
                    bid_qty, bid_price, ask_price, ask_qty = match_tuple
                    # Validate: first and last should be integers (quantities), middle two should be decimals (prices)
                    if (bid_qty.replace(',', '').isdigit() and 
                        '.' in bid_price and 
                        '.' in ask_price and 
                        ask_qty.replace(',', '').isdigit()):
                        data['order_book'].append({
                            'bid_qty': bid_qty,
                            'bid_price': bid_price,
                            'ask_price': ask_price,
                            'ask_qty': ask_qty
                        })
        
        # Look for total buy/sell quantities in the main text
        buy_qty_match = re.search(r'Total Buy Quantity([0-9,.]+)', body_text)
        if buy_qty_match:
            data['total_buy_qty'] = buy_qty_match.group(1)
        
        sell_qty_match = re.search(r'Total Sell Quantity([0-9,.]+)', body_text)
        if sell_qty_match:
            data['total_sell_qty'] = sell_qty_match.group(1)
        
        # Extract returns data (YTD, 1M, 3M, 6M, 1Y, 3Y, 5Y)
        # These are typically shown as percentages in specific sections
        data['returns'] = {}
        
        # Find all text elements containing percentages
        percent_texts = soup.find_all(string=lambda t: t and '%' in t and len(t.strip()) < 50)
        
        for text in percent_texts:
            text_stripped = text.strip()
            parent = text.find_parent()
            if not parent or parent.name in ['style', 'script']:
                continue
            
            # Get the context around this percentage
            parent_text = parent.get_text(strip=True)
            
            # Look for return period indicators
            # Patterns like "YTD26.26%" or "1M3.54%"
            for period in ['YTD', '1M', '3M', '6M', '1Y', '3Y', '5Y', '10Y', '15Y', '20Y', '25Y', '30Y']:
                if period in parent_text:
                    # Extract the percentage near this period
                    period_match = re.search(period + r'\s*([0-9.]+%)', parent_text)
                    if period_match:
                        data['returns'][period] = period_match.group(1)
        
    except Exception as e:
        data['parse_error'] = str(e)
    
    return data


async def scrape_with_homepage_search(
    symbol: str,
    output_dir: str = "output",
    headless: bool = False,
    take_screenshot: bool = True,
) -> dict:
    """
    Scrape NSE equity quote by searching from homepage.
    
    Opens NSE homepage, searches for symbol, clicks first suggestion,
    and extracts all equity quote data.
    
    Args:
        symbol: Stock symbol to search (e.g., "RELIANCE", "TCS")
        output_dir: Directory to save outputs
        headless: Run browser in headless mode
        take_screenshot: Whether to take screenshot
    
    Returns:
        dict: Contains status, paths to saved files, and parsed data
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    domain = "www_nseindia_com"
    screenshot_path = os.path.join(output_dir, f"{domain}_quote_{timestamp}.png")
    html_path = os.path.join(output_dir, f"{domain}_quote_{timestamp}.html")
    json_path = os.path.join(output_dir, f"{domain}_quote_{timestamp}.json")
    
    # Handle headed mode in headless environments (e.g., Railway)
    # This will raise RuntimeError if headed mode is requested but DISPLAY is not available
    actual_headless, additional_args = get_browser_launch_args(headless)
    
    if actual_headless:
        print("[WARN] Running in HEADLESS mode")
    else:
        display = os.environ.get('DISPLAY', 'Not set')
        print(f"[INFO] Running in HEADED mode with DISPLAY={display}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=actual_headless,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage', 
                '--disable-gpu',
                '--disable-extensions',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--window-size=1920,1080',
                '--disable-blink-features=AutomationControlled',
                '--disable-http2'
            ] + additional_args,
        )
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            ignore_https_errors=True,
            java_script_enabled=True,
            reduced_motion='no-preference'
        )
        
        page = await context.new_page()
        
        # Hide automation flags
        await page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            """
        )
        
        # Extra headers
        await page.set_extra_http_headers(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        )
        
        try:
            # Navigate to NSE homepage
            print("[INFO] Opening NSE homepage...")
            homepage_url = "https://www.nseindia.com"
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Use 'load' for headless mode, 'domcontentloaded' for non-headless
                    wait_strategy = "load" if headless else "domcontentloaded"
                    timeout_val = 120000 if headless else 60000  # Longer timeout for headless
                    
                    await page.goto(
                        homepage_url,
                        wait_until=wait_strategy,
                        timeout=timeout_val
                    )
                    await human_delay(2, 4)
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"[WARN] Attempt {attempt + 1} failed, retrying...: {e}")
                        await human_delay(3, 6)
                    else:
                        # Last attempt - try with minimal wait
                        try:
                            await page.goto(homepage_url, wait_until="commit", timeout=30000)
                            await human_delay(3, 5)
                        except:
                            raise
            
            print("[INFO] Waiting for page to fully load...")
            await human_delay(2, 4)
            
            # Move mouse to simulate activity
            await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            await human_delay(0.5, 1)
            
            # Find the search input field on homepage
            print(f"[INFO] Looking for search input field on homepage...")
            input_selectors = [
                '#header-search-input',
                'input.typeahead.tt-input',
                'input[placeholder*="Search"]',
                'input[placeholder*="company"]',
                'input[placeholder*="symbol"]',
                'input[type="text"]',
            ]
            
            input_field = None
            for selector in input_selectors:
                try:
                    elements = page.locator(selector)
                    count = await elements.count()
                    if count > 0:
                        input_field = elements.first
                        if await input_field.is_visible():
                            print(f"[SUCCESS] Found input field with selector: {selector}")
                            break
                except:
                    continue
            
            if not input_field:
                print(f"[ERROR] Could not find search input field on homepage")
                await context.close()
                await browser.close()
                return {
                    "status": "error",
                    "error": "Could not find search input field on homepage"
                }
            
            # Scroll to input field
            await input_field.scroll_into_view_if_needed()
            await human_delay(1, 2)
            
            # Move mouse to input field
            box = await input_field.bounding_box()
            if box:
                await page.mouse.move(int(box['x'] + box['width'] / 2), int(box['y'] + box['height'] / 2))
            await human_delay(0.5, 1.5)
            
            # Click the input field
            print(f"[INFO] Clicking on search input field...")
            await input_field.click()
            await human_delay(1, 2)
            
            # Clear any existing text
            await input_field.press("Control+A")
            await human_delay(0.2, 0.4)
            await input_field.press("Backspace")
            await human_delay(0.3, 0.7)
            
            # Type symbol with realistic delays
            print(f"[INFO] Typing '{symbol}' in search field...")
            for char in symbol:
                await input_field.type(char, delay=random.randint(50, 150))
                await human_delay(0.05, 0.2)
            
            print(f"[INFO] Waiting for suggestions to appear...")
            await human_delay(3, 5)
            
            # Find and click the first suggestion
            print(f"[INFO] Looking for first suggestion...")
            suggestion_selectors = [
                '.tt-suggestion',
                '#autoCompleteBlock li',
                '.autocompleteList li',
                'div.autocompleteList li',
                '.ng-option',
                'a.ng-option',
                '[role="option"]',
                '#autoCompleteBlock a',
            ]
            
            suggestion_found = False
            for selector in suggestion_selectors:
                try:
                    suggestions = page.locator(selector)
                    count = await suggestions.count()
                    if count > 0:
                        print(f"[SUCCESS] Found {count} suggestions with selector: {selector}")
                        
                        # Click the first suggestion
                        first_suggestion = suggestions.first
                        try:
                            suggestion_text = await first_suggestion.inner_text()
                            print(f"[INFO] Clicking first suggestion: {suggestion_text}")
                            
                            is_visible = await first_suggestion.is_visible(timeout=2000)
                            if is_visible:
                                await first_suggestion.scroll_into_view_if_needed()
                                await human_delay(0.3, 0.8)
                                
                                await first_suggestion.click(force=True, timeout=10000)
                                print(f"[SUCCESS] Clicked first suggestion successfully")
                                await human_delay(1, 2)
                                suggestion_found = True
                                break
                        except Exception as e:
                            print(f"[WARN] Error clicking first suggestion: {str(e)}")
                            continue
                except Exception as e:
                    print(f"[DEBUG] Failed with selector '{selector}': {str(e)}")
                    continue
            
            if not suggestion_found:
                print(f"[WARN] Could not find suggestions, trying keyboard navigation...")
                await human_delay(0.5, 1)
                await input_field.press("ArrowDown")
                await human_delay(0.3, 0.8)
                await input_field.press("Enter")
                await human_delay(2, 4)
            
            print(f"[INFO] Waiting for navigation to quote page...")
            await human_delay(3, 5)
            
            # Wait for the quote page to load
            try:
                # Wait for main content to appear - longer timeout in headless mode
                selector_timeout = 45000 if headless else 30000
                await page.wait_for_selector('main#midBody', timeout=selector_timeout)
                print("[INFO] Quote page loaded")
            except Exception as e:
                print(f"[WARN] Main content selector not found (continuing anyway): {e}")
            
            # Additional wait for dynamic content - CRITICAL for order book table
            # Longer wait in headless mode as it may be slower
            wait_time = (8, 12) if headless else (5, 8)
            print(f"[INFO] Waiting for dynamic content (including order book) to load...")
            await human_delay(wait_time[0], wait_time[1])
            
            # Scroll to trigger lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)
            await page.evaluate("window.scrollTo(0, 0)")
            await human_delay(3, 5)
            
            # Scroll to middle to ensure order book section loads
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await human_delay(2, 4)
            
            # Try to wait for order book table specifically
            # Use JavaScript to check if order book has loaded
            print("[INFO] Waiting specifically for order book table...")
            order_book_loaded = False
            max_attempts = 10
            for attempt in range(max_attempts):
                try:
                    # Check if order book exists in DOM using JavaScript
                    order_book_check = await page.evaluate("""
                        () => {
                            // Check for order book table
                            const tables = document.querySelectorAll('table');
                            for (let table of tables) {
                                const text = table.textContent || '';
                                if ((text.includes('Bid') || text.includes('bid')) && 
                                    (text.includes('Ask') || text.includes('ask')) && 
                                    (text.includes('Qty') || text.includes('qty'))) {
                                    const rows = table.querySelectorAll('tbody tr, tr');
                                    if (rows.length >= 2) {
                                        return true;
                                    }
                                }
                            }
                            // Check for order book label
                            const labels = document.querySelectorAll('span.order-book-label, [class*="order"], [id*="order"]');
                            for (let label of labels) {
                                if (label.textContent && label.textContent.toLowerCase().includes('order')) {
                                    return true;
                                }
                            }
                            return false;
                        }
                    """)
                    
                    if order_book_check:
                        print(f"[SUCCESS] Order book detected in DOM (attempt {attempt + 1})")
                        order_book_loaded = True
                        await human_delay(2, 3)
                        break
                    else:
                        print(f"[INFO] Order book not yet loaded, waiting... (attempt {attempt + 1}/{max_attempts})")
                        await human_delay(2, 3)
                except Exception as e:
                    print(f"[WARN] Error checking for order book: {e}")
                    await human_delay(1, 2)
            
            if not order_book_loaded:
                print("[WARN] Order book may not have loaded - will attempt to extract anyway")
                # Try waiting for common selectors as fallback
                try:
                    selector_timeout = 10000 if headless else 5000
                    await page.wait_for_selector('table.table, span.order-book-label, [class*="order"]', timeout=selector_timeout)
                    print("[INFO] Order book elements detected via selector")
                except Exception as e:
                    print(f"[WARN] Order book table selector not found: {e}")
            
            # Final wait to ensure all data is rendered
            wait_time = (3, 5) if headless else (2, 4)
            await human_delay(wait_time[0], wait_time[1])
            
            # Move mouse to simulate activity
            await page.mouse.move(random.randint(200, 600), random.randint(200, 600))
            await human_delay(0.5, 1.0)
            
            # Scroll a bit
            await page.mouse.wheel(0, random.randint(200, 600))
            await human_delay(0.5, 1.0)
            
            # Extra wait for dynamic content to fully load
            await human_delay(3, 6)
            
            if take_screenshot:
                print("[INFO] Taking screenshot...")
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"[SUCCESS] Screenshot saved: {screenshot_path}")
            
            print("[INFO] Extracting order book data directly from DOM...")
            # Try to extract order book using JavaScript before saving HTML
            # IMPORTANT: Include all rows, even if they contain "-" values (as requested by user)
            order_book_data = await page.evaluate("""
                () => {
                    const orderBook = [];
                    
                    // First, try to find the OrderData div specifically
                    const orderDataDiv = document.querySelector('div.OrderData');
                    if (orderDataDiv) {
                        const table = orderDataDiv.querySelector('table.table');
                        if (table) {
                            const tbody = table.querySelector('tbody');
                            if (tbody) {
                                const rows = tbody.querySelectorAll('tr');
                                for (let row of rows) {
                                    const cells = row.querySelectorAll('td');
                                    if (cells.length >= 4) {
                                        const entry = {
                                            'bid_qty': (cells[0].textContent || '').trim() || '-',
                                            'bid_price': (cells[1].textContent || '').trim() || '-',
                                            'ask_price': (cells[2].textContent || '').trim() || '-',
                                            'ask_qty': (cells[3].textContent || '').trim() || '-'
                                        };
                                        orderBook.push(entry);
                                    }
                                }
                                if (orderBook.length > 0) {
                                    return orderBook;
                                }
                            }
                        }
                    }
                    
                    // Fallback: Find all tables
                    const tables = document.querySelectorAll('table');
                    
                    for (let table of tables) {
                        const tableText = table.textContent || '';
                        const hasBid = tableText.includes('Bid') || tableText.includes('bid');
                        const hasAsk = tableText.includes('Ask') || tableText.includes('ask');
                        const hasQty = tableText.includes('Qty') || tableText.includes('qty');
                        
                        if (hasBid && hasAsk && hasQty) {
                            const rows = table.querySelectorAll('tbody tr, tr');
                            
                            if (rows.length > 1) {
                                // Get headers to understand structure
                                const headerRow = rows[0];
                                const headerCells = headerRow.querySelectorAll('th, td');
                                const headers = Array.from(headerCells).map(cell => 
                                    (cell.textContent || '').trim().toUpperCase()
                                );
                                
                                // Find column indices
                                let qtyIdx = null, bidIdx = null, askIdx = null, askQtyIdx = null;
                                
                                for (let i = 0; i < headers.length; i++) {
                                    const header = headers[i].replace(/[₹()]/g, '').trim();
                                    if (header.includes('QTY') && qtyIdx === null) {
                                        qtyIdx = i;
                                    } else if (header.includes('BID')) {
                                        bidIdx = i;
                                    } else if (header.includes('ASK')) {
                                        askIdx = i;
                                    } else if (header.includes('QTY') && qtyIdx !== null) {
                                        askQtyIdx = i;
                                    }
                                }
                                
                                // Default to positional if indices not found
                                if (qtyIdx === null) qtyIdx = 0;
                                if (bidIdx === null) bidIdx = 1;
                                if (askIdx === null) askIdx = 2;
                                if (askQtyIdx === null) askQtyIdx = 3;
                                
                                // Extract data rows - include ALL values, even if "-"
                                for (let i = 1; i < rows.length; i++) {
                                    const row = rows[i];
                                    const cells = row.querySelectorAll('td, th');
                                    
                                    if (cells.length >= 4) {
                                        const entry = {
                                            'bid_qty': (cells[qtyIdx]?.textContent || '').trim() || '-',
                                            'bid_price': (cells[bidIdx]?.textContent || '').trim() || '-',
                                            'ask_price': (cells[askIdx]?.textContent || '').trim() || '-',
                                            'ask_qty': (cells[askQtyIdx]?.textContent || '').trim() || '-'
                                        };
                                        
                                        // Always add the entry, even if all values are "-"
                                        orderBook.push(entry);
                                    }
                                }
                                
                                if (orderBook.length > 0) {
                                    break; // Found order book, stop searching
                                }
                            }
                        }
                    }
                    
                    return orderBook;
                }
            """)
            
            print(f"[INFO] Extracted {len(order_book_data)} order book entries from DOM")
            
            print("[INFO] Saving HTML content...")
            html_content = await page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"[SUCCESS] HTML saved: {html_path}")
            
            print("[INFO] Parsing HTML to extract data...")
            parsed_data = parse_nse_quote_html(html_content)
            
            # Merge JavaScript-extracted order book with parsed data
            if order_book_data and len(order_book_data) > 0:
                print(f"[SUCCESS] Using {len(order_book_data)} order book entries from DOM extraction")
                parsed_data['order_book'] = order_book_data
            elif parsed_data.get('order_book'):
                print(f"[INFO] Using {len(parsed_data.get('order_book', []))} order book entries from HTML parsing")
            else:
                print("[WARN] No order book data found in either DOM or HTML")
            
            # Debug: Check if data was extracted
            if not parsed_data or len(parsed_data) <= 1:
                print(f"[WARN] Limited data extracted. Keys found: {list(parsed_data.keys())}")
                if 'main#midBody' in html_content or 'id="midBody"' in html_content:
                    print("[INFO] Main body found in HTML")
                else:
                    print("[WARN] Main body NOT found in HTML - page may not have loaded correctly")
            
            # Save parsed JSON
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(parsed_data, f, indent=2, ensure_ascii=False)
            print(f"[SUCCESS] Parsed JSON saved: {json_path}")
            
            await context.close()
            await browser.close()
            
            return {
                "status": "success",
                "symbol": symbol,
                "url": page.url,
                "screenshot": screenshot_path if take_screenshot else None,
                "html": html_path,
                "json": json_path,
                "data": parsed_data,
                "timestamp": timestamp,
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to scrape: {e}")
            await context.close()
            await browser.close()
            return {
                "status": "error",
                "symbol": symbol,
                "error": str(e),
            }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NSE Dashboard Scraper - Search from homepage and scrape equity quote data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dashbord.py -s RELIANCE
  python dashbord.py -s TCS
  python dashbord.py -s INFY -o ./custom_output
  python dashbord.py -s HDFC --headless --no-screenshot
        """
    )
    
    parser.add_argument(
        '-s', '--symbol',
        required=True,
        help='Stock symbol to search (e.g., RELIANCE, TCS, INFY, HDFC, ICICI)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='output',
        help='Output directory for screenshots and HTML files (default: output)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run in headless mode (no browser window)'
    )
    
    parser.add_argument(
        '--no-screenshot',
        action='store_true',
        help='Skip taking screenshot'
    )
    
    args = parser.parse_args()
    
    # Print header
    print("[START] NSE Dashboard Scraper")
    print(f"Mode: JavaScript Rendering Enabled | Headless: {args.headless} | Screenshot: {not args.no_screenshot}")
    print(f"Stock Symbol: {args.symbol}\n")
    
    result = asyncio.run(
        scrape_with_homepage_search(
            symbol=args.symbol.upper(),
            output_dir=args.output,
            headless=args.headless,
            take_screenshot=not args.no_screenshot,
        )
    )
    
    if result.get("status") == "success":
        print("\n" + "="*60)
        print("[FINAL] ✓ Scraping completed successfully!")
        print("="*60)
        print(f"  Symbol:     {result['symbol']}")
        print(f"  URL:        {result['url']}")
        print(f"  Screenshot: {result.get('screenshot', 'N/A')}")
        print(f"  HTML:       {result['html']}")
        print(f"  JSON:       {result['json']}")
        
        # Print summary of parsed data
        parsed_data = result.get('data', {})
        if parsed_data and 'error' not in parsed_data:
            print("\n[DATA SUMMARY]")
            if 'symbol' in parsed_data:
                print(f"  Symbol: {parsed_data['symbol']}")
            if 'last_price' in parsed_data:
                print(f"  Last Price: {parsed_data['last_price']}")
            if 'change' in parsed_data and 'percent_change' in parsed_data:
                print(f"  Change: {parsed_data['change']} ({parsed_data['percent_change']})")
            if 'open' in parsed_data:
                print(f"  Open: {parsed_data['open']}")
            if 'high' in parsed_data:
                print(f"  High: {parsed_data['high']}")
            if 'low' in parsed_data:
                print(f"  Low: {parsed_data['low']}")
            if 'prev_close' in parsed_data:
                print(f"  Prev. Close: {parsed_data['prev_close']}")
        else:
            print("\n[WARN] Limited or no data extracted")
            if 'error' in parsed_data:
                print(f"  Error: {parsed_data['error']}")
    else:
        print("\n[FINAL] ✗ Scraping failed")
        print(f"  Error: {result.get('error')}")

