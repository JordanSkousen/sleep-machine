import subprocess
import RPi.GPIO as gpio

gpio.setmode(gpio.BCM)

gpio_pin = 4

gpio.setup(gpio_pin, gpio.IN)

prev_val = -1
connected = False
speaker_mac = "F8:0F:F9:BF:9C:E0"
cvlc_process = None

print("ready")

try:
    while True:
        val = gpio.input(gpio_pin)
        if val == 0 and prev_val == 1:
            if not connected:
                subprocess.run(["bluetoothctl", "connect", speaker_mac])
                cvlc_process = subprocess.Popen(["cvlc", "--repeat", "file:///home/jordan/Downloads/Aircraft Lavatory.mp3"])
            else:              
                cvlc_process.kill()
                cvlc_process = None
                subprocess.run(["bluetoothctl", "disconnect", speaker_mac])
            connected = not connected
        prev_val = val
except KeyboardInterrupt:
    print("Exiting")
finally:
    if cvlc_process is not None:
        cvlc_process.kill()
    gpio.cleanup()

