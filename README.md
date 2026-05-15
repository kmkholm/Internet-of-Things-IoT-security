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

> _(Add screenshots of Dashboard, Monitor, CoAP, Zigbee here)_

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
