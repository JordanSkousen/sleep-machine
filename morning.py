from datetime import datetime
import random
from google import genai
from google.genai import types
import requests
from bs4 import BeautifulSoup
from elevenlabs import tts

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

def get_morning_announcement():
    """
    Generates a morning announcement with weather and a fun fact.
    """
    client = genai.Client() # GEMINI_API_KEY environment variable automatically set by Client

    fun_fact = pick_random_funfact()
    forecast_summary = get_weather()
    if forecast_summary:
        today = datetime.now().strftime("%B %d, %Y")
        prompt = f"You are a easy-going, silly weather man reporting today's forecast. Today's forecast is {forecast_summary}. Today's date is {today}. Give the weather report for today, then throw in this fun fact: \"{fun_fact}\". Keep it under 200 words."

        print("Generating morning announcement...", flush=True)
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=types.Part.from_text(text=prompt)
            )
            # I tried including asking for a fun fact in the gemini prompt, but it kept giving me the same fun fact "A group of owls is called a parliament" lol
            print("Announcement text generated:", flush=True)
            print(response.text, flush=True)
            return response.text
        except Exception as e:
            print(f"An error occurred during content generation: {e}", flush=True)
            return fun_fact
        finally:
            client.close()
    else:
        return f"Here's a random fun fact: {fun_fact}"

def generate_morning_announcement(output_file):
    """
    Main function to generate and save the morning announcement.
    """
    # You can change the location here
    announcement = get_morning_announcement()
    if announcement:
        return tts(announcement, output_filename=output_file)

if __name__ == "__main__":
    generate_morning_announcement("morning_announcement.mp3")