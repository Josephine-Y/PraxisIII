from machine import Pin
import time

SENSOR_PIN = 16

PULSES_PER_ROTATION = 1

MEASUREMENT_INTERVAL = 2.0

DEBOUNCE_MS = 15

WIND_SPEED_FACTOR = 1.0


pulse_count = 0
last_pulse_time = 0

sensor = Pin(SENSOR_PIN, Pin.IN)

def count_pulse(pin):
    global pulse_count, last_pulse_time

    now = time.ticks_ms()

    if time.ticks_diff(now, last_pulse_time) > DEBOUNCE_MS:
        pulse_count += 1
        last_pulse_time = now


sensor.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=count_pulse)


print("Sensor pin:", SENSOR_PIN)
print("Pulses per rotation:", PULSES_PER_ROTATION)
print("Measurement interval:", MEASUREMENT_INTERVAL, "seconds")
print("Debounce:", DEBOUNCE_MS, "ms")
print("Wind speed factor:", WIND_SPEED_FACTOR)


while True:
    pulse_count = 0

    # Mark the start time
    start_time = time.ticks_ms()

    # Wait until the measurement interval is finished
    while time.ticks_diff(time.ticks_ms(), start_time) < int(MEASUREMENT_INTERVAL * 1000):
        time.sleep_ms(10)

    counted_pulses = pulse_count
    pulses_per_second = counted_pulses / MEASUREMENT_INTERVAL
    rotations_per_second = pulses_per_second / PULSES_PER_ROTATION
    rpm = rotations_per_second * 60
    estimated_wind_speed = rotations_per_second * WIND_SPEED_FACTOR
    print("Wind speed estimate:  ", estimated_wind_speed)
