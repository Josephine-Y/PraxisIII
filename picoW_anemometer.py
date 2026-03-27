from machine import Pin
import time

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

# Count BOTH rising and falling edges.
# For a latching sensor with alternating N/S poles, each valid state change is useful.
hall_sensor.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=hall_callback)

# -----------------------------
# MAIN LOOP
# -----------------------------


while True:
    pulse_count = 0
    start_time = time.ticks_ms()

    time.sleep(SAMPLE_TIME)

    elapsed_s = time.ticks_diff(time.ticks_ms(), start_time) / 1000

    # Rotations per second
    rev_per_sec = (pulse_count / PULSES_PER_REV) / elapsed_s

    # Tangential speed at radius
    circumference = 2 * 3.14159265359 * radius
    cup_speed_m_s = rev_per_sec * circumference

    # Estimated wind speed
    wind_speed_m_s = cup_speed_m_s * CALIBRATION_FACTOR
    wind_speed_km_h = wind_speed_m_s * 3.6

    print("Pulses:", pulse_count)
    print("RPS:", round(rev_per_sec, 3))
    print("Wind Speed: {:.2f} m/s | {:.2f} km/h".format(wind_speed_m_s, wind_speed_km_h))
