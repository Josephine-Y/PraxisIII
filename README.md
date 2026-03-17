# PraxisIII

This repo holds the files to implement a 4-node sensor network of thermistors that send temperature data to a specified server node. The server node communicates through Flask API to a webpage deployed through Render.

The stack is as follows:
Sensor Client --> Sensor Server --> Flask --> Supabase --> Flask --> Render

To make your own sensor network, follow the instructions below:

1. Set up Raspberrry Pi Pico Ws (files in picoW_setup/)

   For each Raspberry Pi Pico W...
   
      a. Hold down the BOOTSEL button and plug in the Raspberry Pi Pico W to your laptop using a micro-USB to USB-A or USB-C cable. File Explorer should pop up,
   
      b. Add the adafruit-circuitpython-raspberry_pi_pico_w-en_US-10.0.3.uf2. The name of the folder should change to CIRCUITPYTHON.
   
