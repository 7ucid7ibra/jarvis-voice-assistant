
![[Pasted image 20251213142425.png]]

# Aqara Motion and Light Sensor P2

**Core Description:** Indoor smart motion and light sensor using PIR motion detection and ambient light sensing. Communicates via Matter over Thread.

## Technical Specifications
- **Model:** ML-S03E / ML-S03D
- **Protocol:** Thread, Bluetooth 5.0
- **Battery:** 2x CR2450 (up to 2 years life)
- **Dimensions:** 33.1 × 33.1 × 41.6 mm
- **Operating Range:** -10°C to 55°C, 95% humidity
- **Motion Detection:** 170° field of view, up to 7m range
- **Light Sensing:** Up to 1500 lux

## Connectivity & Compatibility
- **Matter Support:** Native Matter over Thread
- **Requires:** Thread border router (e.g., HomePod mini, Aqara Hub M3)
- **Ecosystems:** Apple Home, Google Home, Amazon Alexa, Samsung SmartThings, Home Assistant
- **Note:** Not compatible with older Aqara hubs without Thread/Matter

## Features
- Dual sensing: motion detection and light measurement
- Automations: trigger lights, cameras, alerts based on motion/light
- Local control: works without cloud when border router present
- LED indicators for status

## Use Cases
- Security: detect presence, trigger alerts
- Lighting: auto on/off based on occupancy/light
- Energy efficiency: adjust HVAC/lighting
- Cross-platform integration via Matter

## Limitations
- Thread endpoint only (no routing)
- Feature exposure varies by ecosystem
- Battery life depends on usage
- Advanced settings may require Aqara app

