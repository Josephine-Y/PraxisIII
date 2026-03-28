# 1.1.1_verification.py
# Pico W (CircuitPython) thermistor verification logger
# Prints temperature for exactly 30 seconds from start of run.

import time
import board
import analogio
import math

# -----------------------------
# Thermistor setup (same as your main code)
# -----------------------------
adc = analogio.AnalogIn(board.GP26)

SERIES_RESISTOR = 10000        # ohms
NOMINAL_RESISTANCE = 10000     # ohms at nominal temperature
NOMINAL_TEMP_C = 25            # degC
BETA = 3950                    # beta value
VREF = 3.3                     # Pico W ADC reference voltage

def get_temp_c_from_adc(adc_value: int) -> float:
    # Convert ADC reading to voltage
    voltage = (adc_value / 65535) * VREF

    # Avoid divide-by-zero / invalid values near rails
    if voltage <= 0.001 or voltage >= (VREF - 0.001):
        return float("nan")

    # Convert voltage divider output to thermistor resistance
    resistance = SERIES_RESISTOR * (voltage / (VREF - voltage))

    # Beta equation -> temperature in Kelvin
    temp_k = 1.0 / (
        (1.0 / (NOMINAL_TEMP_C + 273.15)) + (1.0 / BETA) * math.log(resistance / NOMINAL_RESISTANCE)
    )
    return temp_k - 273.15

def get_temp_avg(samples: int = 5, sample_delay_s: float = 0.02) -> float:
    total = 0.0
    valid = 0
    for _ in range(samples):
        t = get_temp_c_from_adc(adc.value)
        if not math.isnan(t):
            total += t
            valid += 1
        time.sleep(sample_delay_s)
    return total / valid if valid > 0 else float("nan")

# -----------------------------
# Measurement settings
# -----------------------------
DURATION_S = 10.0
AVG_SAMPLES = 5

# Choose an update interval for printing.
# With AVG_SAMPLES=5 and sample_delay_s=0.02, you already spend ~0.10 s sampling.
# This keeps prints readable without slowing you down too much.
PRINT_INTERVAL_S = 0.5

# -----------------------------
# Run test
# -----------------------------
print("Starting 30s temperature verification...")
print("time_s,temp_c")

start = time.monotonic()
next_print = start

temps = []  # store samples for mean/std

while True:
    now = time.monotonic()
    elapsed = now - start

    if elapsed >= DURATION_S:
        break

    # Only print/log on the chosen interval
    if now >= next_print:
        temp_c = get_temp_avg(AVG_SAMPLES)
        temps.append(temp_c)

        line = f"{elapsed:.2f},{temp_c:.2f}"
        print(line)

        next_print += PRINT_INTERVAL_S

# Compute summary stats (mean, std dev)
# Use population std dev here; if you prefer sample std dev, use (n-1) in denominator.
n = len(temps)
valid_temps = [t for t in temps if not math.isnan(t)]
m = len(valid_temps)

if m == 0:
    print("\nNo valid temperature samples collected (check wiring / sensor).")
else:
    mean = sum(valid_temps) / m
    var = sum((t - mean) ** 2 for t in valid_temps) / m
    std = math.sqrt(var)

    print("\n--- 10s Summary ---")
    print(f"samples_collected: {n} (valid: {m})")
    print(f"mean_temp_c: {mean:.2f}")
    print(f"std_temp_c:  {std:.2f}")
    print("-------------------")
