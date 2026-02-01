import datetime
import random
from google import genai
from google.genai import types
import os
import requests
from elevenlabs import tts

def get_weather(location):
    """
    Fetches weather from wttr.in
    """
    print(f"Getting weather...")
    try:
        response = requests.get(f"https://wttr.in/{location}?format=j1")
        response.raise_for_status()  # Raise an exception for bad status codes
        weather_data = response.json()
        today_forecast = weather_data['weather'][0]
        conditions = today_forecast['hourly'][4]['weatherDesc'][0]['value']
        high_temp_f = today_forecast['maxtempF']
        return conditions, high_temp_f
    except requests.exceptions.RequestException as e:
        print(f"Could not retrieve weather: {e}")
        return None, None
    
def pick_random_funfact():
    """Read funfacts.txt and return a random line."""
    with open("funfacts.txt", 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    return random.choice(lines)

def get_morning_announcement(location):
    """
    Generates a morning announcement with weather and a fun fact.
    """
    client = genai.Client() # GEMINI_API_KEY environment variable automatically set by Client

    fun_fact = pick_random_funfact()
    conditions, high = get_weather(location)
    if conditions and high:
        today = datetime.datetime.now().strftime("%B %d, %Y")
        prompt = f"You are a easy-going, silly weather man reporting today's forecast. Today's forecast for {location} is {conditions} with a high of {high} degrees Fahrenheit. Today's date is {today}. Give the weather report for today. Keep it under 100 words." if conditions and high else "Tell me a random fun fact."

        print("Generating morning announcement...")
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=types.Part.from_text(text=prompt)
            )
            # I tried including asking for a fun fact in the gemini prompt, but it kept giving me the same fun fact "A group of owls is called a parliament" lol
            announcement_text = f"{response.text}\nAnd finally, here's a random fun fact for the day: {fun_fact}"
            print("Announcement text generated:")
            print(announcement_text)
            return announcement_text
        except Exception as e:
            print(f"An error occurred during content generation: {e}")
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
    announcement = get_morning_announcement(location="Pleasant Grove, Utah")
    if announcement:
        return tts(announcement, output_filename=output_file)

if __name__ == "__main__":
    generate_morning_announcement()
