

# 🔬 IoT Protocol Simulator

A modern, all-in-one teaching and research tool for IoT messaging protocols, built with Python and CustomTkinter.

Simulates **MQTT, MQTTS, CoAP, AMQP, Zigbee, Z-Wave, and NFC** in a single dark-themed GUI with live sensor dashboards, real-time plots, and color-coded protocol logs.

## ✨ Features

- **📊 Dashboard** — 12 live virtual sensors (temperature, humidity, pressure, light, CO₂, gas, PM2.5, sound, heart rate, vibration, UV, motion) with mean-reverting random-walk models. Publishes JSON telemetry over MQTT/MQTTS at adjustable rate (0.5–10 Hz) with live matplotlib plots in a 3×4 grid.
- **📡 Monitor** — MQTT subscriber that auto-discovers sensors from incoming topics and plots them in real time.
- **📨 MQTT / 🔒 MQTTS** — Full publisher/subscriber with QoS 0/1/2, retain flag, username/password, multiple public broker presets (HiveMQ, EMQX, Mosquitto), and CONNACK timeout warnings.
- **🌐 CoAP** — RFC 7252 client + server with live resource management. Add, edit, and remove resources on a running server with no restart. Pre-loaded examples + `/.well-known/core` discovery.
- **🐰 AMQP 0-9-1** — Works **without RabbitMQ** using a built-in in-memory broker. Full direct/fanout/topic/headers routing. Optional Real RabbitMQ mode via `pika`.
- **🐝 Zigbee** — IEEE 802.15.4 + ZCL simulator. PAN ID, channels 11–26, AES-128-CCM* keys, device templates (Smart Light, Dimmer, Plug, Temp/Humidity/Motion sensors), full ZCL frame logging.
- **📡 Z-Wave** — Sub-GHz mesh simulator. 32-bit Home ID, 6 regional frequencies, S0/S2 security, command classes (Switch Binary, Multilevel, Sensor, Battery, Version, etc.), inclusion mode.
- **📱 NFC** — NDEF tag simulator (no hardware needed). Type 1–5 tags, records for Text/URI/WiFi/SmartPoster/vCard/MIME/External, hex dump, JSON/binary export.

---

## 📦 Installation

```bash
git clone git@github.com:kmkholm/Internet-of-Things-IoT-security.git
cd iot-protocol-simulator
pip install -r requirements.txt
python iot_protocol_simulatorv.py
```

### Dependencies






# Internet-of-Things-IoT-security

> ⚠️ **Important:** install with the same Python that runs the script. On startup, the terminal prints the Python executable path so you can verify.

---

## 🚀 Quick Start

### End-to-end MQTT demo (one window)

1. Open the **📊 Dashboard** tab
2. Protocol = `MQTT`, Broker = `broker.hivemq.com`, Port = `1883`, Prefix = `iot/demo`
3. Click **Connect** → wait for green ● Connected
4. Click **▶ Start** — sensors begin publishing
5. Open the **📡 Monitor** tab, same broker/port, Topic = `iot/demo/+`
6. Click **Connect & Subscribe** — sensors appear on the Monitor as plots

### CoAP demo

1. Open **🌐 CoAP** → click **▶ Start Server** (5 example resources pre-loaded)
2. Click **🔍 GET** next to `/sensor/temp` → see `RX code=2.05 Content payload='22.5'`
3. Change method to **PUT**, type a value, click **Send** → resource updates live in the list

### AMQP demo (no RabbitMQ needed)

1. Open **🐰 AMQP** — Local Simulator mode is on by default
2. **Declare Exchange** (topic) → **Declare + Bind Queue** → **▶ Start Consuming** → **📤 Publish**
3. Log shows full produce/route/deliver chain

### Zigbee demo

1. Open **🐝 Zigbee** → **▶ Form Network**
2. Pick "Smart Light", click **+ Join Device**
3. Select the light, cluster `On/Off`, command `Toggle`, click **📤 Send ZCL** → device state flips

---

## 🛠️ Tech Stack

| Protocol | Library | Status |
|----------|---------|--------|
| MQTT / MQTTS | `paho-mqtt` | Real |
| CoAP | `aiocoap` | Real |
| AMQP | `pika` + built-in simulator | Both |
| NDEF | `ndeflib` + fallback encoder | Real |
| Zigbee / Z-Wave | Pure-Python simulation | Sim |
| UI | `customtkinter` | — |
| Plotting | `matplotlib` | — |

---

## 📸 Screenshots

<img width="1918" height="998" alt="zigbee" src="https://github.com/user-attachments/assets/7c99d3ec-edae-4203-acc7-7fe5a2e6a12c" />


---

## 👤 Author

**Dr. Mohammed Tawfik**
Assistant Professor — Cybersecurity & Cloud Computing
Ajloun National University · Sana'a University

📧 kmkhol01@gmail.com

---

## 📄 License

MIT License — free for academic, teaching, and research use.

---

## 🤝 Contributing

Pull requests welcome. For major changes, please open an issue first to discuss what you'd like to change.
