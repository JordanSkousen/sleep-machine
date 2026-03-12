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

def get_weather():
    """
    Fetches weather from wunderground.com
    """
    print(f"Getting weather from Wunderground...", flush=True)
    try:
        response = requests.get("https://www.wunderground.com/weather/us/ut/pleasant-grove")
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Using CSS selector to find the forecast summary
        # The query is div.columns.small-12 > a.module-link
        forecast_element = soup.select_one('div.columns.small-12 > a.module-link')
        
        if forecast_element:
            forecast_summary = forecast_element.get_text(strip=True)
            return forecast_summary
        else:
            print("Could not find forecast summary on the page.", flush=True)
            return None
    except requests.exceptions.RequestException as e:
        print(f"Could not retrieve weather: {e}", flush=True)
        return None
    
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

def get_morning_announcement(personality = pick_random_personality(), attempt=0):
    """
    Generates a morning announcement with weather and a fun fact.
    """
    with open(".previous_personalities", 'a') as f:
        f.write(personality['name'] + "\n")
    client = genai.Client() # GEMINI_API_KEY environment variable automatically set by Client

    fun_fact = pick_random_funfact()
    forecast_summary = get_weather()

    today = datetime.now().strftime("%B %d, %Y")
    name = personality['name']
    voice_id = personality['voice_id']
    base_prompt = personality['prompt']

    prompt = f"Your name is {name}. {base_prompt} Today's forecast is {forecast_summary}. Today's date is {today}. Give the weather report for today, then throw in this fun fact: \"{fun_fact}\". Keep it under 200 words." if forecast_summary != None else \
        f"Your name is {name}. {base_prompt} Unfortunately you were unable to determine today's forecast before getting on. Create an excuse as to why you are unprepared. Finally, make sure to throw in this fun fact: \"{fun_fact}\". Keep it under 200 words."

    print(f"Generating morning announcement with personality: {name}", flush=True)
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
        print(f"An error occurred during content generation: {e}", flush=True)
        if attempt < 3:
            print(f"Trying to generate morning announcement again (attempt {attempt + 1}/3)...")
            time.sleep(2)
            get_morning_announcement(attempt=attempt + 1)
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
    generate_morning_announcement("morning_announcement.mp3")
    #get_morning_announcement()
    #print(pick_random_personality())
