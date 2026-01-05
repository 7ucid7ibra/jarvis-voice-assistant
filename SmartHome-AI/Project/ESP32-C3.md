![[Pasted image 20251213142922.png]]![[Pasted image 20251213143657.png]]
# ESP32-C3 Round Display Module

Waveshare ESP32-C3-LCD-0.71: Compact microcontroller with round color LCD for wearables and small devices.

## Core
- ESP32-C3 RISC-V MCU (32-bit, Wi-Fi + BLE)
- Integrated flash
- USB-C for power/programming (native USB-CDC)

## Display
- 0.71-inch round TFT (240×240 resolution)
- SPI-driven, MCU-controlled backlight
- Ideal for watch/badge-style devices

## Board Layout
- Buttons: BOOT, RST
- Battery input: VBAT (Li-ion/Li-Po support)
- Power pads: 5V, 3.3V
- Mounting holes, FPC connector for LCD
- USB-C at bottom

## Electronics
- PMIC + charger for single-cell battery
- 3.3V regulator
- SPI to LCD, side pads only (no large GPIO header)
- Ultra-compact design

## Use Cases
- Wearables
- UI badges
- Sensor displays
- BLE companions
- IoT indicators