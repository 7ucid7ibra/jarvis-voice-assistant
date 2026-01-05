![[Pasted image 20251213143847.png]]
# ESP32-S3-Touch-LCD-1.85C-BOX

All-in-one ESP32-S3 smart box with HMI, audio, and battery for voice/touch interfaces.

## Core MCU
- **SoC:** ESP32-S3 (Dual-core Xtensa LX7, 240 MHz)
- **Memory:** 512 KB SRAM, 384 KB ROM, 16 MB Flash, 8 MB PSRAM
- **AI:** Vector instructions
- **USB:** Native USB-OTG

## Wireless
- **Wi-Fi:** 2.4 GHz 802.11 b/g/n
- **Bluetooth:** BLE 5.0 only
- **Antenna:** Onboard PCB

## Display & Touch
- **LCD:** 1.85" round, 360×360 resolution, 262K colors
- **Interface:** SPI (display), I²C (touch)
- **Touch:** Capacitive with interrupt
- **GUI:** Optimized for LVGL

## Audio System
- **Microphone:** Onboard
- **Codec:** Integrated decoder/amplifier
- **Speaker:** Via onboard amp
- **Use cases:** Voice assistants, wake-word detection, audio playback

## Storage & Power
- **Storage:** TF/microSD slot
- **Battery:** Integrated Li-ion/Li-Po with charging IC
- **Power modes:** Light/deep sleep, RTC wake

## I/O & Interfaces
- **Interfaces:** UART, I²C, SPI, GPIO (limited), USB
- **Clock:** Flexible for power optimization

## Physical Form Factor
- **Enclosure:** Pre-assembled smart-speaker box
- **Interaction:** Touch + voice + display
- **Target:** Finished device prototyping

## Software Ecosystem
- **SDK:** ESP-IDF, Arduino support
- **GUI:** LVGL, TFT_eSPI/LovyanGFX
- **Audio:** ESP-ADF
- **Stacks:** Wi-Fi dashboards, voice assistants, IoT panels, AI edge UI

## Use Cases
- Smart speakers/voice terminals
- Home assistant nodes
- IoT control panels
- AI voice/touch interfaces
- Portable HMI devices

## Key Features
- Large PSRAM (8 MB)
- Integrated audio/mic/battery
- Round touch display
- Product-like enclosure

## Constraints
- BLE only (no Classic Bluetooth)
- Limited GPIO
- Circular UI layouts required
