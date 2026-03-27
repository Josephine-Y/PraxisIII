from machine import Pin
import time

# -----------------------------
# USER SETTINGS
# -----------------------------

HALL_PIN = 16
PULSES_PER_REV = 2
radius = 0.3
CALIBRATION_FACTOR = 1.0
SAMPLE_TIME = 1.0
DEBOUNCE_MS = 3

TEST_DURATION = 120  # seconds (2 minutes)

# -----------------------------
# GLOBAL VARIABLES
# -----------------------------

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
# MAIN TEST LOOP (2 MINUTES)
# -----------------------------

reading_count = 0
test_start = time.ticks_ms()

while time.ticks_diff(time.ticks_ms(), test_start) < TEST_DURATION * 1000:
    pulse_count = 0
    start_time = time.ticks_ms()

    time.sleep(SAMPLE_TIME)

    elapsed_s = time.ticks_diff(time.ticks_ms(), start_time) / 1000

    rev_per_sec = (pulse_count / PULSES_PER_REV) / elapsed_s
    circumference = 2 * 3.14159265359 * radius
    cup_speed_m_s = rev_per_sec * circumference

    wind_speed_m_s = cup_speed_m_s * CALIBRATION_FACTOR
    wind_speed_km_h = wind_speed_m_s * 3.6

    reading_count += 1

    print("Wind Speed: {:.2f} m/s | {:.2f} km/h".format(wind_speed_m_s, wind_speed_km_h))

# -----------------------------
# RESULTS
# -----------------------------

total_time_s = time.ticks_diff(time.ticks_ms(), test_start) / 1000
sampling_rate_hz = reading_count / total_time_s

print("Total readings:", reading_count)
print("Sampling rate: {:.2f} Hz".format(sampling_rate_hz))
