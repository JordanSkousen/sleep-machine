import RPi.GPIO as GPIO
import time

# Pin definitions
CLK_PIN = 4
SW_PIN = 2

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(CLK_PIN, GPIO.IN)
GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Variables to store the state
counter = 0
clk_last_state = GPIO.input(CLK_PIN)
button_last_state = GPIO.input(SW_PIN)

print("Rotary encoder test program")
print("Press Ctrl+C to exit")

try:
    while True:
        clk_state = GPIO.input(CLK_PIN)
        button_state = GPIO.input(SW_PIN)

        # Rotary encoder logic
        if clk_state != clk_last_state and clk_state == 1:
            counter += 1
            print(f"Counter: {counter}")
        clk_last_state = clk_state

        # Button logic
        if button_state != button_last_state:
            if button_state == GPIO.LOW:
                print("Button pressed")
        button_last_state = button_state

        time.sleep(0.01)

except KeyboardInterrupt:
    print("Exiting...")
finally:
    GPIO.cleanup()