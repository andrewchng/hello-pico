from machine import Pin
import time

led = Pin(15, Pin.OUT)
btn = Pin(16, Pin.IN, Pin.PULL_UP)
debounce_time = 50  # milliseconds
last_state = btn.value()
last_change = time.ticks_ms()

while True:
    v = btn.value()
    current_time = time.ticks_ms()

    # Check for state change with debounce
    if v != last_state and time.ticks_diff(current_time, last_change) > debounce_time:
        last_state = v
        last_change = current_time
        if v == 0:  # Button pressed
            led.toggle()  # Toggle LED state
   