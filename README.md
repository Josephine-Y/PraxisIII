# PraxisIII

This repo holds the files to implement a 4-node sensor network of thermistors that send temperature data to a specified server node. The server node communicates through Flask API to a webpage deployed through Render.

The stack is as follows:
Sensor Client --> Sensor Server --> Flask --> Supabase --> Flask --> Render

To make your own sensor network, follow the instructions below:

1. Set up the node network's Raspberry Pi Pico Ws (files in picoW_setup/)

   For each Raspberry Pi Pico W...
   
      a. Enter Bootloader mode: Hold the BOOTSEL button while connecting the Raspberry Pi Pico W to your laptop using a micro-USB to USB-A or USB-C cable, then release when File Explorer appers as RPI-RP2
   
      b. Drop adafruit-circuitpython-raspberry_pi_pico_w-en_US-10.0.3.uf2 onto the mounted drive (RPI-RP2) (download the .uf2 file from https://circuitpython.org/board/raspberry_pi_pico_w/). The name of the drive should change to CIRCUITPYTHON.



2. Set up the anemometer's Raspberry Pi Pico W

   a. Enter Bootloader mode: Hold the BOOTSEL button while connecting the Raspberry Pi Pico W to your laptop using a micro-USB to USB-A or USB-C cable, then release when File Explorer appers as RPI-RP2
   
   b. Drop RPI_PICO_W-20251209-v1.27.0.uf2 onto the mounted drive (RPI-RP2) (download the .uf2 file from https://micropython.org/download/RPI_PICO_W/). MicroPython does not support File Explorer. Must interact with the board through Thonny or the command-line over the USB connection.
