import subprocess
import RPi.GPIO as GPIO
from datetime import datetime, timedelta
import time
import threading
from eightsleep import EightSleep
from morning import generate_morning_announcement

cvlc_process = None
def play_file(file, repeat=False):
    global cvlc_process
    if cvlc_process:
        cvlc_process.kill()
    print(f"Playing {file}")
    cvlc_process = subprocess.Popen(
        ["cvlc", "--repeat", f"file://{file}"] if repeat else ["cvlc", f"file://{file}"])
    
def play_file_sync(file):
    subprocess.run(["cvlc", "--play-and-exit", f"file://{file}"])

def stop_playback():
    global cvlc_process
    if cvlc_process:
        cvlc_process.kill()
        cvlc_process = None

# --- GPIO Setup ---
CLK_PIN = 4
SW_PIN = 2
GPIO.setmode(GPIO.BCM)
GPIO.setup(CLK_PIN, GPIO.IN)
GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# --- State Variables ---
clk_last_state = GPIO.input(CLK_PIN)
button_last_state = GPIO.input(SW_PIN)
white_noise_playing = False
speaker_mac = "F8:0F:F9:BF:9C:E0"
alarm_mode = False
backwards_mode = False
click_timer = None
click_count = 0
alarm_announced = False
alarm_has_gone_off_today = False
alarm_presets = [
    [8, 30], # Mon
    [8, 30], # Tue
    [8, 30], # Wed
    [8, 30], # Thu
    [10, 0], # Fri
    [10, 0], # Sat
    [8, 30], # Sun
]
dow = datetime.now().weekday()
alarm_hour = alarm_presets[dow][0]
alarm_minute = alarm_presets[dow][1]
last_interaction = datetime.now()

# --- Configuration ---
SOUND_PATH = "/home/jordan/source/repos/sleep-machine/"
WHITE_NOISE_FILE = "Aircraft Lavatory extended.mp3"
ALARM_FILE = "alarm.mp3"
POD_TEMP = -45
eight_sleep = EightSleep()

subprocess.run(["bluetoothctl", "connect", speaker_mac])
time.sleep(2) # wait a few secs b/c bluetooth is glitchy for first few secs after connecting
print("ready")

def handle_clicks():
    global click_count, white_noise_playing, backwards_mode, alarm_hour, alarm_minute, eight_sleep, last_interaction, announce_ready_state, play_file, alarm_has_gone_off_today, SOUND_PATH, WHITE_NOISE_FILE, POD_TEMP

    if click_count == 1:
        # Single click action
        if last_interaction > datetime.now() + timedelta(minutes=5):
            # Announce ready state instead of toggling backwards mode
            announce_ready_state()
        else:
            # Toggle backwards mode
            backwards_mode = not backwards_mode
            mode_str = "backwards" if backwards_mode else "forwards"
            print(f"Alarm adjustment set to {mode_str}")
            announcement_file = f"{SOUND_PATH}tts/{mode_str}.mp3"
            threading.Thread(target=play_file, args=(announcement_file,)).start()

    elif click_count == 2:
        # Double click action
        if alarm_has_gone_off_today: # Check the lock
            print("Cannot play white noise, alarm has already gone off today.")
            threading.Thread(target=play_file, args=(f"{SOUND_PATH}tts/notallowed.mp3",)).start()
        else:
            print("Playing white noise")
            play_file(f"{SOUND_PATH}{WHITE_NOISE_FILE}", repeat=True)
            white_noise_playing = True
            backwards_mode = False
            alarm_hour = datetime.now().hour # For debugging
            alarm_minute = datetime.now().minute + 1 # For debugging
            if not eight_sleep.is_pod_on:
                try:
                    eight_sleep.set_pod_state(True)
                    eight_sleep.set_temperature(POD_TEMP)
                except:
                    print("Failed to turn on pod")

    click_count = 0


def announce_ready_state():
    play_file_sync(f"{SOUND_PATH}tts/ready.mp3")
    play_file_sync(f"{SOUND_PATH}tts/{alarm_hour}{alarm_minute}.mp3")
    play_file_sync(f"{SOUND_PATH}tts/currenttime.mp3")
    play_file_sync(f"{SOUND_PATH}tts/int/{datetime.now().hour}.mp3")
    play_file_sync(f"{SOUND_PATH}tts/int/{datetime.now().minute}.mp3")

announce_ready_state()

try:
    while True:
        clk_state = GPIO.input(CLK_PIN)
        button_state = GPIO.input(SW_PIN)
        now = datetime.now()

        # Reset the alarm lock at 9:00 PM (21:00)
        if alarm_has_gone_off_today and now.hour >= 21:
            alarm_has_gone_off_today = False
            print("Alarm lock removed. White noise can be played.")

        if not eight_sleep.is_pod_on and now.hour >= 11:
            try:
                eight_sleep.set_pod_state(True)
                eight_sleep.set_temperature(POD_TEMP)
            except:
                print("Failed to turn on pod")
            

        # --- Alarm Trigger Logic ---
        if (not alarm_mode and white_noise_playing and now.hour == alarm_hour and now.minute == alarm_minute):
            print("Alarm triggered")
            play_file(f"{SOUND_PATH}{ALARM_FILE}")
            alarm_mode = True
            alarm_has_gone_off_today = True # Set the lock

        # --- Potentiometer Logic ---
        if not white_noise_playing and clk_state != clk_last_state and clk_state == 1:
            last_interaction = now
            alarm_time = datetime.now().replace(hour=alarm_hour, minute=alarm_minute, second=0, microsecond=0)
            if alarm_time.hour >= 4 and alarm_time.hour <= 12:
                if backwards_mode:
                    alarm_time -= timedelta(minutes=15)
                else:
                    alarm_time += timedelta(minutes=15)

            alarm_hour = alarm_time.hour
            alarm_minute = alarm_time.minute

            announcement = f"Alarm set to {alarm_hour:02d}:{alarm_minute:02d}"
            announcement_file = f"{SOUND_PATH}tts/{alarm_hour}{alarm_minute}.mp3"
            threading.Thread(target=play_file, args=(announcement_file,)).start()

        # --- Button Logic ---
        if button_state != button_last_state and button_state == GPIO.LOW:
            last_interaction = now
            if click_timer:
                click_timer.cancel()
            if alarm_mode:
                click_count = 0
                print("Stopping alarm")
                stop_playback()
                morning_file = "/tmp/morning.mp3"
                if generate_morning_announcement(morning_file):
                    threading.Thread(target=play_file, args=(morning_file,)).start()
                else:
                    threading.Thread(target=play_file, args=(f"{SOUND_PATH}tts/gmorn.mp3",)).start()
                alarm_mode = False
                white_noise_playing = False
                try:
                    eight_sleep.set_pod_state(False)
                except:
                    print("Failed to turn off pod")

            elif white_noise_playing:
                click_count = 0
                print("Stopping white noise")
                stop_playback()
                white_noise_playing = False
                try:
                    eight_sleep.set_pod_state(False)
                except:
                    print("Failed to turn off pod")
            else:
                click_count += 1
                click_timer = threading.Timer(0.3, handle_clicks)
                click_timer.start()

        clk_last_state = clk_state
        button_last_state = button_state
        time.sleep(0.01)

except KeyboardInterrupt:
    print("Exiting")
finally:
    if click_timer is not None:
        click_timer.cancel()
    if cvlc_process is not None:
        cvlc_process.kill()
    subprocess.run(["bluetoothctl", "disconnect", speaker_mac])
    GPIO.cleanup()
