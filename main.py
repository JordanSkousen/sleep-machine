import subprocess
import RPi.GPIO as GPIO
from datetime import datetime, timedelta
import time
import threading
import os
from eightsleep import EightSleep
from morning import generate_morning_announcement

cvlc_process = None
def play_file(file, repeat=False):
    global cvlc_process
    stop_playback()
    print(f"Playing {file}", flush=True)
    cvlc_process = subprocess.Popen(
        ["cvlc", "--repeat", f"file://{file}"] if repeat else ["cvlc", f"file://{file}"])
    
def play_file_sync(file):
    print(f"Playing {file}", flush=True)
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
alarm_mode = False
backwards_mode = False
click_timer = None
click_count = 0
alarm_announced = False
alarm_time = datetime.now()
last_interaction = datetime.now()
eight_sleep = EightSleep()

# --- Configuration ---
ALARM_PRESETS = [
    [8, 30], # Mon night (goes off Tue morning)
    [8, 30], # Tue night (goes off Wed morning)
    [8, 30], # Wed night (goes off Thu morning)
    [8, 30], # Thu night (goes off Fri morning)
    [10, 0], # Fri night (goes off Sat morning)
    [10, 0], # Sat night (goes off Sun morning)
    [8, 30], # Sun night (goes off Mon morning)
]
SOUND_PATH = "/home/jordan/source/repos/sleep-machine/"
WHITE_NOISE_FILE = "Aircraft Lavatory medium extended.mp3"
ALARM_FILE = "alarm.mp3"
POD_TEMP = -45
SPEAKER_MAC = "F8:0F:F9:BF:9C:E0"
LAST_ALARM_FILE = "last_alarm.txt"

def get_last_alarm_time():
    if not os.path.exists(LAST_ALARM_FILE):
        return None
    with open(LAST_ALARM_FILE, "r") as f:
        content = f.read().strip()
        if content:
            try:
                return datetime.fromisoformat(content)
            except ValueError:
                return None
    return None

def write_last_alarm_time():
    with open(LAST_ALARM_FILE, "w") as f:
        f.write(datetime.now().isoformat())

def alarm_lock_is_active():
    last_alarm = get_last_alarm_time()
    if not last_alarm:
        return False
    
    now = datetime.now()
    # If alarm was on a previous day, lock is off
    if now.date() > last_alarm.date():
        return False
    
    # If alarm was today, lock is active until 9pm
    if now.hour >= 21:
        return False # Lock is lifted at 9pm
    
    return True # Lock is active

def handle_clicks():
    global click_count, white_noise_playing, alarm_time, backwards_mode, eight_sleep, last_interaction, set_default_alarm_and_announce_ready, play_file, SOUND_PATH, WHITE_NOISE_FILE, POD_TEMP

    now = datetime.now()
    if click_count == 1:
        # Single click action
        if (now - last_interaction) >= timedelta(minutes=5):
            # Announce ready state instead of toggling backwards mode
            set_default_alarm_and_announce_ready()
        else:
            # Toggle backwards mode
            backwards_mode = not backwards_mode
            mode_str = "backwards" if backwards_mode else "forwards"
            print(f"Alarm adjustment set to {mode_str}", flush=True)
            announcement_file = f"{SOUND_PATH}tts/{mode_str}.mp3"
            threading.Thread(target=play_file, args=(announcement_file,)).start()

    elif click_count == 2:
        # Double click action
        if alarm_lock_is_active(): # Check the lock
            print("Cannot play white noise, alarm has already gone off today.", flush=True)
            threading.Thread(target=play_file, args=(f"{SOUND_PATH}tts/notallowed.mp3",)).start()
        else:
            print("Playing white noise", flush=True)
            play_file(f"{SOUND_PATH}{WHITE_NOISE_FILE}", repeat=True)
            white_noise_playing = True
            backwards_mode = False
            #alarm_time = alarm_time.replace(day=now.day, hour=now.hour, minute=now.minute + 1) # For debugging
            if alarm_time < now: # if current time is before midnight, the alarm time will be in the past -- move alarm time to tomorrow
                alarm_time = alarm_time + timedelta(days=1)
            if not eight_sleep.is_pod_on:
                try:
                    eight_sleep.set_pod_state(True)
                    eight_sleep.set_temperature(POD_TEMP)
                except:
                    print("Failed to turn on pod", flush=True)

    click_count = 0


def set_default_alarm_and_announce_ready():
    global alarm_time, ALARM_PRESETS
    now = datetime.now()
    dow = (now - timedelta(hours=3)).weekday() # When calculating the day of week, subtract 3 from the current hour so that on Sun from 12:00am-3:00am it chooses the Sat time to wake up (10:00am)
    alarm_time = now.replace(hour=ALARM_PRESETS[dow][0], minute=ALARM_PRESETS[dow][1], second=0, microsecond=0)
    play_file_sync(f"{SOUND_PATH}tts/ready.mp3")
    print(f"Set alarm time: {alarm_time}", flush=True)
    play_file_sync(f"{SOUND_PATH}tts/{alarm_time.hour}{alarm_time.minute}.mp3")

subprocess.run(["bluetoothctl", "connect", SPEAKER_MAC])
time.sleep(2) # wait a few secs b/c bluetooth is glitchy for first few secs after connecting
print("ready", flush=True)
set_default_alarm_and_announce_ready()
# announce the current time on start up, so if the system time is wrong the user knows
play_file_sync(f"{SOUND_PATH}tts/currenttime.mp3")
play_file_sync(f"{SOUND_PATH}tts/int/{datetime.now().hour}.mp3")
play_file_sync(f"{SOUND_PATH}tts/int/{datetime.now().minute}.mp3")

try:
    while True:
        clk_state = GPIO.input(CLK_PIN)
        button_state = GPIO.input(SW_PIN)
        now = datetime.now()

        if not eight_sleep.is_pod_on and now.hour >= 11:
            try:
                eight_sleep.set_pod_state(True)
                eight_sleep.set_temperature(POD_TEMP)
            except:
                print("Failed to turn on pod", flush=True)

        # --- Alarm Trigger Logic ---
        if (not alarm_mode and white_noise_playing and now >= alarm_time):
            print("Alarm triggered", flush=True)
            play_file(f"{SOUND_PATH}{ALARM_FILE}")
            alarm_mode = True
            write_last_alarm_time() # Set the lock

        # --- Potentiometer Logic ---
        if not white_noise_playing and clk_state != clk_last_state and clk_state == 1:
            last_interaction = now
            if alarm_time.hour >= 4 and alarm_time.hour <= 12:
                if backwards_mode:
                    alarm_time -= timedelta(minutes=15)
                else:
                    alarm_time += timedelta(minutes=15)

            announcement = f"Alarm set to {alarm_time.strftime("%H:%M")}"
            announcement_file = f"{SOUND_PATH}tts/{alarm_time.hour}{alarm_time.minute}.mp3"
            threading.Thread(target=play_file, args=(announcement_file,)).start()

        # --- Button Logic ---
        if button_state != button_last_state and button_state == GPIO.LOW:
            last_interaction = now
            if click_timer:
                click_timer.cancel()
            if alarm_mode:
                click_count = 0
                alarm_mode = False
                white_noise_playing = False
                print("Stopping alarm", flush=True)
                stop_playback()
                morning_file = "/tmp/morning.mp3"
                if generate_morning_announcement(morning_file):
                    threading.Thread(target=play_file, args=(morning_file,)).start()
                else:
                    threading.Thread(target=play_file, args=(f"{SOUND_PATH}tts/gmorn.mp3",)).start()
                try:
                    eight_sleep.set_pod_state(False)
                except:
                    print("Failed to turn off pod", flush=True)

            elif white_noise_playing:
                click_count = 0
                print("Stopping white noise", flush=True)
                stop_playback()
                white_noise_playing = False
                try:
                    eight_sleep.set_pod_state(False)
                except:
                    print("Failed to turn off pod", flush=True)
            else:
                click_count += 1
                click_timer = threading.Timer(0.3, handle_clicks)
                click_timer.start()

        clk_last_state = clk_state
        button_last_state = button_state
        time.sleep(0.01)

except KeyboardInterrupt:
    print("Exiting", flush=True)
finally:
    if click_timer is not None:
        click_timer.cancel()
    stop_playback()
    subprocess.run(["bluetoothctl", "disconnect", SPEAKER_MAC])
    GPIO.cleanup()
