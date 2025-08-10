import time
import math
import random
import sys
try:
    import uselect as select  # MicroPython
except ImportError:
    import select
from machine import Pin
from neopixel import myNeopixel


# Hardware setup
NUM_LEDS = 8
DATA_PIN = 16
np = myNeopixel(NUM_LEDS, DATA_PIN)


# Helpful color tuples
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)
ORANGE = (255, 120, 0)
CYAN = (0, 255, 200)
MAGENTA = (255, 0, 180)
OFF = (0, 0, 0)


def set_all(color):
    np.fill(color[0], color[1], color[2])
    np.show()


def scale_color(color, factor):
    r, g, b = color
    return (
        max(0, min(255, int(r * factor))),
        max(0, min(255, int(g * factor))),
        max(0, min(255, int(b * factor)))
    )


def color_wheel(pos):
    # 0-255 color wheel -> (r,g,b)
    pos = pos % 255
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def rainbow_cycle(wait_ms=15, cycles=2):
    # Smooth moving rainbow across the strip
    steps = 255 * cycles
    for step in range(steps):
        for led_index in range(NUM_LEDS):
            color = color_wheel(step + (led_index * 255 // NUM_LEDS))
            np.set_pixel(led_index, color[0], color[1], color[2])
        np.show()
        time.sleep_ms(wait_ms)


def theater_chase(color, wait_ms=80, cycles=24):
    # Classic marquee-style chasing lights
    for _ in range(cycles):
        for phase in range(3):
            for led_index in range(NUM_LEDS):
                if (led_index + phase) % 3 == 0:
                    np.set_pixel(led_index, color[0], color[1], color[2])
                else:
                    np.set_pixel(led_index, 0, 0, 0)
            np.show()
            time.sleep_ms(wait_ms)


def comet(color, tail_length=5, wait_ms=40, bounce=True, cycles=2):
    # Bright head with fading tail that moves across the strip
    effective_tail = max(1, tail_length)
    travel = NUM_LEDS - 1
    sequence = list(range(0, travel + 1))
    if bounce:
        sequence = sequence + list(range(travel - 1, 0, -1))

    for _ in range(cycles):
        for head in sequence:
            # Draw tail
            for i in range(NUM_LEDS):
                np.set_pixel(i, 0, 0, 0)
            for offset in range(effective_tail):
                idx = head - offset
                if 0 <= idx < NUM_LEDS:
                    factor = max(0.0, 1.0 - (offset / effective_tail))
                    r, g, b = scale_color(color, factor)
                    np.set_pixel(idx, r, g, b)
            np.show()
            time.sleep_ms(wait_ms)


def sparkle(density=0.25, fade_factor=0.75, wait_ms=30, duration_ms=4000):
    # Random sparkles on black background with gradual fade
    # Note: we directly fade the internal pixel buffer for efficiency
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < duration_ms:
        # Fade all existing pixels by fade_factor
        for i in range(NUM_LEDS):
            packed = np.pixels[i]
            b = packed & 0xFF
            r = (packed >> 8) & 0xFF
            g = (packed >> 16) & 0xFF
            r = int(r * fade_factor)
            g = int(g * fade_factor)
            b = int(b * fade_factor)
            np.pixels[i] = b | (r << 8) | (g << 16)

        # Create a few new sparkles
        sparkles_to_add = max(1, int(NUM_LEDS * density * 0.5))
        for _ in range(sparkles_to_add):
            idx = random.randint(0, NUM_LEDS - 1)
            # Random pastel-ish sparkle
            hue = random.randint(0, 254)
            base = color_wheel(hue)
            r, g, b = scale_color(base, 0.9)
            np.set_pixel(idx, r, g, b)

        np.show()
        time.sleep_ms(wait_ms)


def breathe(color, cycles=2, period_ms=1800, step_ms=20):
    # Smooth cosine-based brightness breathing effect
    total_steps = max(1, period_ms // step_ms)
    for _ in range(cycles):
        for step in range(total_steps):
            phase = (2 * math.pi * step) / total_steps
            factor = 0.15 + 0.85 * (0.5 - 0.5 * math.cos(phase))
            r, g, b = scale_color(color, factor)
            np.fill(r, g, b)
            np.show()
            time.sleep_ms(step_ms)


# --- Non-blocking serial menu helpers ---
def _make_key_reader():
    try:
        poller = select.poll()
        poller.register(sys.stdin, select.POLLIN)

        def read_key_nonblocking():
            if poller.poll(0):
                try:
                    return sys.stdin.read(1)
                except:
                    return None
            return None

        return read_key_nonblocking
    except Exception:
        def read_key_nonblocking():
            try:
                readable, _, _ = select.select([sys.stdin], [], [], 0)
                if readable:
                    return sys.stdin.read(1)
            except:
                return None
            return None

        return read_key_nonblocking


READ_KEY = _make_key_reader()


def print_menu():
    print("\nChoose an effect:")
    print("[1] Rainbow")
    print("[2] Comet")
    print("[3] Theater chase")
    print("[4] Sparkle")
    print("[5] Breathe")
    print("[0] All off")
    print("[q] Quit\n")


# --- Small-step effect runners for responsiveness ---
STATE = {
    "rainbow_step": 0,
    "theater_phase": 0,
    "comet_head": 0,
    "comet_dir": 1,
    "breathe_step": 0,
}


def rainbow_run(step_count=8, wait_ms=10):
    for _ in range(step_count):
        base = STATE["rainbow_step"]
        for led_index in range(NUM_LEDS):
            color = color_wheel(base + (led_index * 255 // NUM_LEDS))
            np.set_pixel(led_index, color[0], color[1], color[2])
        np.show()
        time.sleep_ms(wait_ms)
        STATE["rainbow_step"] = (STATE["rainbow_step"] + 1) % 255


def theater_run(color=CYAN, step_count=6, wait_ms=60):
    for _ in range(step_count):
        phase = STATE["theater_phase"]
        for led_index in range(NUM_LEDS):
            if (led_index + phase) % 3 == 0:
                np.set_pixel(led_index, color[0], color[1], color[2])
            else:
                np.set_pixel(led_index, 0, 0, 0)
        np.show()
        time.sleep_ms(wait_ms)
        STATE["theater_phase"] = (STATE["theater_phase"] + 1) % 3


def comet_run(color=ORANGE, tail_length=6, step_count=1, wait_ms=35):
    travel = NUM_LEDS - 1
    for _ in range(step_count):
        head = STATE["comet_head"]
        direction = STATE["comet_dir"]
        for i in range(NUM_LEDS):
            np.set_pixel(i, 0, 0, 0)
        effective_tail = max(1, tail_length)
        for offset in range(effective_tail):
            idx = head - offset
            if 0 <= idx < NUM_LEDS:
                factor = max(0.0, 1.0 - (offset / effective_tail))
                r, g, b = scale_color(color, factor)
                np.set_pixel(idx, r, g, b)
        np.show()
        time.sleep_ms(wait_ms)
        head += direction
        if head >= travel:
            head = travel
            direction = -1
        elif head <= 0:
            head = 0
            direction = 1
        STATE["comet_head"] = head
        STATE["comet_dir"] = direction


def sparkle_run(duration_ms=180, wait_ms=25, density=0.35, fade_factor=0.78):
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < duration_ms:
        for i in range(NUM_LEDS):
            packed = np.pixels[i]
            b = packed & 0xFF
            r = (packed >> 8) & 0xFF
            g = (packed >> 16) & 0xFF
            r = int(r * fade_factor)
            g = int(g * fade_factor)
            b = int(b * fade_factor)
            np.pixels[i] = b | (r << 8) | (g << 16)
        sparkles_to_add = max(1, int(NUM_LEDS * density * 0.5))
        for _ in range(sparkles_to_add):
            idx = random.randint(0, NUM_LEDS - 1)
            hue = random.randint(0, 254)
            base = color_wheel(hue)
            r, g, b = scale_color(base, 0.9)
            np.set_pixel(idx, r, g, b)
        np.show()
        time.sleep_ms(wait_ms)


def breathe_run(color=MAGENTA, period_ms=1400, step_ms=16, steps_per_call=6):
    total_steps = max(1, period_ms // step_ms)
    for _ in range(steps_per_call):
        s = STATE["breathe_step"]
        phase = (2 * math.pi * s) / total_steps
        factor = 0.15 + 0.85 * (0.5 - 0.5 * math.cos(phase))
        r, g, b = scale_color(color, factor)
        np.fill(r, g, b)
        np.show()
        time.sleep_ms(step_ms)
        STATE["breathe_step"] = (s + 1) % total_steps


def main():
    np.brightness(18)

    EFFECTS = {
        '1': 'Rainbow',
        '2': 'Comet',
        '3': 'Theater chase',
        '4': 'Sparkle',
        '5': 'Breathe',
        '0': 'Off',
    }

    current = '1'
    print_menu()
    print("Selected:", EFFECTS[current])

    try:
        while True:
            key = READ_KEY()
            if key:
                key = key.strip()
                if key == 'q':
                    break
                if key in EFFECTS:
                    current = key
                    print("Selected:", EFFECTS[current])

            if current == '0':
                set_all(OFF)
                time.sleep_ms(40)
            elif current == '1':
                rainbow_run(step_count=8, wait_ms=10)
            elif current == '2':
                comet_run(color=ORANGE, tail_length=6, step_count=1, wait_ms=35)
            elif current == '3':
                theater_run(color=CYAN, step_count=6, wait_ms=60)
            elif current == '4':
                sparkle_run(duration_ms=180, wait_ms=25, density=0.35, fade_factor=0.78)
            elif current == '5':
                breathe_run(color=MAGENTA, period_ms=1400, step_ms=16, steps_per_call=6)
    except KeyboardInterrupt:
        pass
    finally:
        set_all(OFF)


if __name__ == "__main__":
    main()