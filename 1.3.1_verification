import time
import board
import analogio
import math

# -------------------------------
# ADC setup
# Wire 2 (middle of voltage divider) -> GP26 (ADC0)
# -------------------------------
adc = analogio.AnalogIn(board.GP26)  

# -------------------------------
# Thermistor parameters
# -------------------------------
series_resistor = 10000      # 10kΩ fixed resistor
nominal_resistance = 10000   # 10kΩ thermistor at 25°C
nominal_temp = 25            # °C
beta = 3950                  # Beta coefficient from thermistor datasheet

# -------------------------------
# Function to calculate temperature
# -------------------------------
def get_temp(adc_value):
    # ADC returns 0-65535, convert to voltage
    voltage = adc_value / 65535 * 3.3
    # Calculate thermistor resistance
    #resistance = series_resistor * (3.3 / voltage - 1), this decreases temp when you touch the sensor
    
    # If your thermistor is on 3.3V and resistor on GND
    resistance = series_resistor * (voltage / (3.3 - voltage))
    
    # Beta equation to get temperature in Kelvin
    temp_k = 1 / (1/(nominal_temp + 273.15) + (1/beta)*math.log(resistance/nominal_resistance))
    # Convert Kelvin to Celsius
    return temp_k - 273.15

# -------------------------------
# Main loop
# -------------------------------
count = 1
while True:
    temp_c = get_temp(adc.value)
    print("Reading #" + count + ": temp_c))
    time.sleep(1)
    count += 1
