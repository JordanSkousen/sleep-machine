from datetime import datetime
import random
from google import genai
from google.genai import types
import requests
from bs4 import BeautifulSoup
from elevenlabs import tts
import csv
import os
import time
import subprocess

def get_wifi_ssid():
    """Gets the SSID of the currently connected Wi-Fi network (Linux/Debian)."""
    try:
        # Try iwgetid first (common on Debian/Raspberry Pi)
        ssid = subprocess.check_output(['iwgetid', '-r'], stderr=subprocess.DEVNULL).decode('utf-8').strip()
        if ssid:
            return ssid
    except Exception:
        pass

    try:
        # Try nmcli as a fallback (NetworkManager)
        output = subprocess.check_output(['nmcli', '-t', '-f', 'active,ssid', 'dev', 'wifi'], stderr=subprocess.DEVNULL).decode('utf-8')
        for line in output.split('\n'):
            if line.startswith('yes:'):
                return line.split(':', 1)[1].strip()
    except Exception:
        pass

    return None

def get_weather():
    """
    Fetches weather from wunderground.com. The location is based on the currently connected wifi network SSID,
    which is controlled using weather_cities.csv.
    - Columns expected:
        - ssid (e.g. "NETGEAR420")
        - state (e.g. "CA")
        - city (e.g. "Death Valley")
    """
    ssid = get_wifi_ssid()
    if ssid is None:
        return None, None
    
    with open("weather_cities.csv", 'r') as f:
        reader = csv.DictReader(f)
        cities = list(reader)
    city = [city for city in cities if city['ssid'] == ssid][0]
    place_name = f"{city['city']}, {city['state']}"
    print(f"Getting weather from Wunderground for '{place_name}'...", flush=True)
    try:
        state = city['state'].lower()
        city_name = city['city'].lower().replace(" ", "-")
        response = requests.get(f"https://www.wunderground.com/weather/us/{state}/{city_name}")
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Using CSS selector to find the forecast summary
        # The query is div.columns.small-12 > a.module-link
        forecast_element = soup.select_one('div.columns.small-12 > a.module-link')
        
        if forecast_element:
            forecast_summary = forecast_element.get_text(strip=True)
            return place_name, forecast_summary
        else:
            print("Could not find forecast summary on the page.", flush=True)
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"Could not retrieve weather: {e}", flush=True)
        return None, None
    
def get_stock_prices():
    """Gets current stock prices from NASDAQ, reading from stocks.csv to know which tickers to lookup and 
    determine how much money has been earned/lost.
    - Columns expected:
        - ticker (e.g. "APPL")
        - name (e.g. "Apple Inc.")
        - shares (e.g. 420)
        - price (e.g. 69.69)
    - Each row should be a holding in a stock. You can have duplicate rows with the same ticker, for example 
      if you bought the same stock multiple times."""
    with open("stocks.csv", 'r') as f:
        reader = csv.DictReader(f)
        stocks = list(reader)
    tickers = set(x['ticker'] for x in stocks)
    values = []
    for ticker in tickers:
        try:
            print(f"Getting stock price for ticker '{ticker}'...")
            #response.raise_for_status()
            #soup = BeautifulSoup(response.text, 'html.parser')
            #name_el = soup.select_one("section > h1")
            #price_el = soup.select_one(".price.yf-1ommk34.base:not(.up2)")
            response = requests.get(f"https://api.nasdaq.com/api/quote/{ticker}/info?assetclass=stocks", headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'})
            response.raise_for_status()
            response_json = response.json()

            if response_json and response_json['data'] and response_json['data']['primaryData'] and response_json['data']['primaryData']['lastSalePrice']:
                current_price = float(response_json['data']['primaryData']['lastSalePrice'].replace("$", ""))
                applicable_stocks = [stock for stock in stocks if stock['ticker'] == ticker]
                amount_paid = sum(float(stock['shares']) * float(stock['price']) for stock in applicable_stocks)
                amount_holding = sum(float(stock['shares']) * current_price for stock in applicable_stocks)
                values.append({
                    'ticker': ticker,
                    'name': applicable_stocks[0]['name'],
                    'current_price': current_price,
                    'change': f"{response_json['data']['primaryData']['deltaIndicator']} {response_json['data']['primaryData']['percentageChange'].replace('-', '')}",
                    'holding_delta': amount_holding - amount_paid,
                    'holding_pct': (amount_holding - amount_paid) / amount_paid,
                })
            else:
                print(f"Couldn't find current price for stock {ticker}.")
        except requests.exceptions.RequestException as e:
            print(f"Could not lookup stock price: {e}", flush=True)
    return values

def get_stock_summaries():
    stock_prices = get_stock_prices()
    summaries = []
    for stock in stock_prices:
        change_word = "earned" if stock['holding_delta'] > 0 else "lost"
        summaries.append(f"The stock '{stock['name']}' is {stock['change']}, and they have {change_word} ${stock['holding_delta']:,.2f} in the stock so far.")
    return summaries
    
def pick_random_funfact():
    """Read funfacts.txt and return a random line."""
    with open("funfacts.txt", 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    return random.choice(lines)

def pick_random_personality():
    """Read personalities.csv and return a random personality."""
    with open("personalities.csv", 'r') as f:
        reader = csv.DictReader(f)
        personalities = list(reader)
    previous_personalities = []
    if os.path.exists(".previous_personalities"):
        with open(".previous_personalities", 'r') as f:
            previous_personalities = [line.strip() for line in f.readlines() if line.strip()]
        if len(previous_personalities) == len(personalities):
            os.remove(".previous_personalities")
            previous_personalities = [previous_personalities[-1]]
    personality = random.choice(personalities)
    while personality['name'] in previous_personalities:
        personality = random.choice(personalities)
    return personality

def get_morning_announcement(personality=None):
    """
    Generates a morning announcement with weather and a fun fact.
    """
    if personality is None:
        personality = pick_random_personality()

    with open(".previous_personalities", 'a') as f:
        f.write(personality['name'] + "\n")
    client = genai.Client() # GEMINI_API_KEY environment variable automatically set by Client

    fun_fact = pick_random_funfact()
    place_name, forecast_summary = get_weather()
    stock_summaries = " ".join(get_stock_summaries())
    stock_summaries_str = f"Then report on their stock movements, which are: {stock_summaries}" if stock_summaries != "" else ""

    today = datetime.now().strftime("%B %d, %Y")
    name = personality['name']
    voice_id = personality['voice_id']
    base_prompt = personality['prompt']

    prompt = f"Your name is {name}. {base_prompt} Today's forecast for {place_name} is {forecast_summary}. Today's date is {today}. First give the weather report for today. {stock_summaries_str} Finally throw in this fun fact: \"{fun_fact}\". Keep it under 200 words." if forecast_summary != None else \
        f"Your name is {name}. {base_prompt} Unfortunately you were unable to determine today's forecast before getting on. Create an excuse as to why you are unprepared. {stock_summaries_str} Finally, make sure to throw in this fun fact: \"{fun_fact}\". Keep it under 200 words."

    print(f"Generating morning announcement with personality: {name}", flush=True)
    while True:
        attempt = 0
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=types.Part.from_text(text=prompt)
            )
            # I tried including asking for a fun fact in the gemini prompt, but it kept giving me the same fun fact "A group of owls is called a parliament" lol
            print("Announcement text generated:", flush=True)
            print(response.text, flush=True)
            return response.text, voice_id
        except Exception as e:
            print(f"An error occurred calling Gemini: {e}", flush=True)
            if attempt < 3:
                print(f"Trying to generate morning announcement again (attempt {attempt + 1}/3)...")
                attempt = attempt + 1
                time.sleep(2)
            else: 
                return fun_fact, voice_id
        finally:
            client.close()

def generate_morning_announcement(output_file):
    """
    Main function to generate and save the morning announcement.
    """
    # You can change the location here
    announcement, voice_id = get_morning_announcement()
    if announcement:
        return tts(voice_id=voice_id, text=announcement, output_filename=output_file)

if __name__ == "__main__":
    #generate_morning_announcement("morning_announcement.mp3")
    #get_morning_announcement()
    #print(pick_random_personality())
    #print(get_stock_prices())
    print(get_weather())
