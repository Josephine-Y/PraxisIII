# 1.1.2_verification.py
# Pico W (MicroPython) Hall-effect anemometer verification logger
# Runs for exactly 30 seconds from start of run.

from machine import Pin
import time
import math

# -----------------------------
# Hardware / measurement settings
# -----------------------------
SENSOR_PIN = 16

# If one magnet (or one pulse) per rotation, this is 1.
# If you have multiple magnets, set accordingly.
PULSES_PER_ROTATION = 1

# How often to compute/report speed (seconds)
REPORT_INTERVAL_S = 1.0

# Total test duration (seconds)
DURATION_S = 30.0

# Debounce to reject chatter/noise (ms)
DEBOUNCE_MS = 15

# Calibration factor:
# If you haven't calibrated yet, leave as 1.0.
# Later you can set WIND_SPEED_FACTOR so that:
# wind_speed_mps = rotations_per_second * WIND_SPEED_FACTOR
WIND_SPEED_FACTOR = 1.0

# Optional CSV logging
LOG_TO_CSV = False
CSV_FILENAME = "anemometer_verification.csv"

# -----------------------------
# Pulse counting via interrupt
# -----------------------------
pulse_count = 0
last_pulse_ms = 0

sensor = Pin(SENSOR_PIN, Pin.IN)

def count_pulse(pin):
    global pulse_count, last_pulse_ms
    now = time.ticks_ms()
    if time.ticks_diff(now, last_pulse_ms) > DEBOUNCE_MS:
        pulse_count += 1
        last_pulse_ms = now

# For Hall sensors, count *one* edge to avoid double-counting.
sensor.irq(trigger=Pin.IRQ_RISING, handler=count_pulse)

print("Starting 30s anemometer verification...")
print("sensor_pin:", SENSOR_PIN)
print("pulses_per_rotation:", PULSES_PER_ROTATION)
print("report_interval_s:", REPORT_INTERVAL_S)
print("debounce_ms:", DEBOUNCE_MS)
print("wind_speed_factor:", WIND_SPEED_FACTOR)
print("\ntime_s,pulses,rot_per_s,rpm,wind_speed_est")

# Prepare CSV if needed
csv_file = None
if LOG_TO_CSV:
    csv_file = open(CSV_FILENAME, "w")
    csv_file.write("time_s,pulses,rot_per_s,rpm,wind_speed_est\n")

# For summary stats
wind_samples = []

start = time.ticks_ms()
next_report = start
end_time = start + int(DURATION_S * 1000)

# We'll compute speed each report interval based on pulses in that window.
window_start = start
window_start_pulses = 0

while time.ticks_diff(time.ticks_ms(), end_time) < 0:
    now = time.ticks_ms()

    if time.ticks_diff(now, next_report) >= 0:
        # Snapshot pulse count atomically-ish: briefly disable IRQ while reading/resetting baselines
        state = sensor.irq(handler=None)  # disable IRQ
        current_pulses = pulse_count
        sensor.irq(trigger=Pin.IRQ_RISING, handler=count_pulse)  # re-enable

        # Pulses observed in the last window
        pulses_in_window = current_pulses - window_start_pulses
        dt_s = time.ticks_diff(now, window_start) / 1000.0
        if dt_s <= 0:
            dt_s = REPORT_INTERVAL_S

        pulses_per_second = pulses_in_window / dt_s
        rot_per_s = pulses_per_second / PULSES_PER_ROTATION
        rpm = rot_per_s * 60.0
        wind_est = rot_per_s * WIND_SPEED_FACTOR

        elapsed_s = time.ticks_diff(now, start) / 1000.0
        line = "{:.2f},{:d},{:.3f},{:.1f},{:.3f}".format(elapsed_s, pulses_in_window, rot_per_s, rpm, wind_est)
        print(line)

        if csv_file:
            csv_file.write(line + "\n")

        wind_samples.append(wind_est)

        # Advance the window
        window_start = now
        window_start_pulses = current_pulses
        next_report = time.ticks_add(next_report, int(REPORT_INTERVAL_S * 1000))

    # Small sleep to reduce CPU usage
    time.sleep_ms(10)

if csv_file:
    csv_file.close()
    print("\nSaved CSV:", CSV_FILENAME)

# -----------------------------
# Summary stats
# -----------------------------
n = len(wind_samples)
if n == 0:
    print("\nNo samples collected.")
else:
    mean = sum(wind_samples) / n
    var = sum((x - mean) ** 2 for x in wind_samples) / n
    std = math.sqrt(var)

    print("\n--- 30s Summary ---")
    print("samples:", n)
    print("mean_wind_est:", round(mean, 4))
    print("std_wind_est: ", round(std, 4))
    print("-------------------")
