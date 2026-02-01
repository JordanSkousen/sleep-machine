import datetime
import time
import requests
import os

# --- Configuration ---
# IMPORTANT: Replace with your actual ElevenLabs API key.
# You can get one from the ElevenLabs website. It is recommended to use an environment variable.
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# This is the ID for the pre-made 'Rachel' voice. You can find other voice IDs in your Voice Lab.
VOICE_ID = "CwhRBWXzGAHq8TQ4Fs17"

TTS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

HEADERS = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": ELEVENLABS_API_KEY
}

def tts(text: str, output_filename: str = "output.mp3") -> bool:
    print(f"Converting \"{text}\" to mp3...")

    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "language_code": "en",
        "apply_text_normalization": "on",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }

    try:
        response = requests.post(TTS_URL, json=data, headers=HEADERS)

        if response.status_code == 200:
            # The API returns MP3 audio, so it's better to save it as .mp3
            if not output_filename.lower().endswith('.mp3'):
                output_filename += '.mp3'

            with open(output_filename, 'wb') as f:
                f.write(response.content)
            print(f"Success: Audio content written to '{output_filename}'")
            return True
        else:
            print(f"Error from ElevenLabs API: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        return False

if __name__ == '__main__':
    #t = datetime.datetime.now().replace(hour=4, minute=0, second=0, microsecond=0)
    #while t.hour < 13:
    #    tod = "a.m." if t.hour < 12 else "p.m."
    #    min = f":{t.minute:02d}" if t.minute != 0 else ""
    #    tts(f"{t.hour}{min} {tod}", f"tts/{t.hour}{t.minute}")
    #    t += datetime.timedelta(minutes=15)
    for i in range(60):
        tts(f"{i}", f"tts/int/{i}")
    tts(f"Current time is:", "tts/currenttime")