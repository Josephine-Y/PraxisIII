# 1.1.2_verification.py  (MicroPython on Pico W)
# 30-second Hall-effect anemometer verification logger

from machine import Pin
import time
import math

# -----------------------------
# USER SETTINGS
# -----------------------------

HALL_PIN = 16                  # GPIO pin connected to hall sensor output
PULSES_PER_REV = 2             # Number of valid hall state changes per full rotation
radius = 0.3                # Radius from shaft center to cup center (meters)
CALIBRATION_FACTOR = 1.0       # Adjust after testing / calibration
SAMPLE_TIME = 1.0              # Seconds between wind speed calculations
DEBOUNCE_MS = 3                # Ignore very fast false triggers

# -----------------------------
# GLOBAL VARIABLES
# -----------------------------

DURATION_S = 30.0           # verification duration
pulse_count = 0
last_trigger_ms = 0

# -----------------------------
# INTERRUPT CALLBACK
# -----------------------------

def hall_callback(pin):
    global pulse_count, last_trigger_ms

    now = time.ticks_ms()
    if time.ticks_diff(now, last_trigger_ms) > DEBOUNCE_MS:
        pulse_count += 1
        last_trigger_ms = now

# -----------------------------
# SENSOR SETUP
# -----------------------------
hall_sensor = Pin(HALL_PIN, Pin.IN, Pin.PULL_UP)
hall_sensor.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=hall_callback)

# -----------------------------
# HELPER: compute wind speed from pulses
# -----------------------------
CIRCUMFERENCE_M = 2.0 * math.pi * RADIUS_M

def compute_wind_from_pulses(pulses_in_window: int, window_s: float):
    # rotations per second
    rev_per_sec = (pulses_in_window / PULSES_PER_REV) / window_s if window_s > 0 else 0.0
    cup_speed_m_s = rev_per_sec * CIRCUMFERENCE_M
    wind_speed_m_s = cup_speed_m_s * CALIBRATION_FACTOR
    return rev_per_sec, wind_speed_m_s

# -----------------------------
# RUN 30s TEST
# -----------------------------
print("Starting 30s anemometer verification...")
print("time_s,pulses_in_window,rev_per_s,wind_m_s,wind_km_h")

wind_samples = []

start_ms = time.ticks_ms()
end_ms = time.ticks_add(start_ms, int(DURATION_S * 1000))

# window baseline
window_start_ms = start_ms

# snapshot baseline pulses
# (briefly disable IRQ to read pulse_count cleanly)
hall_sensor.irq(handler=None)
baseline_pulses = pulse_count
hall_sensor.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=hall_callback)

next_sample_ms = time.ticks_add(start_ms, int(SAMPLE_TIME_S * 1000))

while time.ticks_diff(time.ticks_ms(), end_ms) < 0:
    now_ms = time.ticks_ms()

    # Take a sample each SAMPLE_TIME_S (e.g., once per second)
    if time.ticks_diff(now_ms, next_sample_ms) >= 0:
        # Snapshot pulse_count safely
        hall_sensor.irq(handler=None)
        current_pulses = pulse_count
        hall_sensor.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=hall_callback)

        pulses_in_window = current_pulses - baseline_pulses
        window_s = time.ticks_diff(now_ms, window_start_ms) / 1000.0

        rev_per_s, wind_m_s = compute_wind_from_pulses(pulses_in_window, window_s)
        wind_km_h = wind_m_s * 3.6

        elapsed_s = time.ticks_diff(now_ms, start_ms) / 1000.0

        line = "{:.2f},{:d},{:.3f},{:.3f},{:.3f}".format(
            elapsed_s, pulses_in_window, rev_per_s, wind_m_s, wind_km_h
        )
        print(line)
        
        wind_samples.append(wind_m_s)

        # reset window baselines
        window_start_ms = now_ms
        baseline_pulses = current_pulses

        # schedule next sample (prevents drift)
        next_sample_ms = time.ticks_add(next_sample_ms, int(SAMPLE_TIME_S * 1000))

    time.sleep_ms(5)

# -----------------------------
# Summary stats for this 30s trial
# -----------------------------
n = len(wind_samples)
if n == 0:
    print("\nNo wind samples collected. Check wiring / sensor / debounce / magnet alignment.")
else:
    mean = sum(wind_samples) / n
    var = sum((x - mean) ** 2 for x in wind_samples) / n
    std = math.sqrt(var)

    print("\n--- 30s Summary ---")
    print("samples:", n)
    print("mean_wind_m_s:", round(mean, 3))
    print("std_wind_m_s: ", round(std, 3))
    print("mean_wind_km_h:", round(mean * 3.6, 3))
    print("-------------------")
