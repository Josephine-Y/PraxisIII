import time
import board
import analogio
import math

# -------------------------------
# ADC setup
# -------------------------------
adc = analogio.AnalogIn(board.GP26)

# -------------------------------
# Thermistor parameters
# -------------------------------
series_resistor = 10000
nominal_resistance = 10000
nominal_temp = 25
beta = 3950

# -------------------------------
# Function to calculate temperature
# -------------------------------
def get_temp(adc_value):
    voltage = adc_value / 65535 * 3.3

    # Thermistor calculation
    resistance = series_resistor * (voltage / (3.3 - voltage))

    temp_k = 1 / (1/(nominal_temp + 273.15) + (1/beta)*math.log(resistance/nominal_resistance))
    return temp_k - 273.15

# -------------------------------
# Main loop (run for 2 minutes)
# -------------------------------
start_time = time.monotonic()
duration = 120  # 2 minutes

reading_count = 0

print("Starting 1.3.1 Verification")

while time.monotonic() - start_time < duration:
    temp_c = get_temp(adc.value)
    reading_count += 1

    #print("Reading #{}: {:.2f} °C".format(reading_count, temp_c))

print("Total readings:", reading_count)
print("Data collection rate: {:.2f} Hz".format(reading_count / 120))
