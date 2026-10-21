<div align="center">

  # 📦 HomeStack
  
  **The ultra-lightweight, self-hosted inventory system for your home, garage, lab, or anything you need to organize.**

  [![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?logo=python&logoColor=white)](#)
  [![Vue.js](https://img.shields.io/badge/Vue-3.x-4FC08D.svg?logo=vuedotjs&logoColor=white)](#)
  [![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](#)
  [![Docker](https://img.shields.io/badge/Docker-Supported-2496ED.svg?logo=docker&logoColor=white)](#)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#)
  
  *Snap a photo, let AI catalog it, and instantly know where everything is.*
</div>

---

## 📸 See it in action

<div align="center">
  <h3>🖥️ Desktop Overview</h3>
  <img src="https://github.com/user-attachments/assets/f68801fd-9ee3-43b2-8220-3959cbf03f3f" alt="HomeStack Desktop View" width="90%" style="border-radius: 10px;" />

  <br/><br/>

  <h3>📱 Mobile App (Light Mode, AI Magic Fill & Dark Mode)</h3>
  <p align="center">
    <img src="https://github.com/user-attachments/assets/63113f02-8c4b-4aef-b394-519c6ed9aa81" alt="Mobile Light Mode" height="460" style="border-radius: 12px; margin: 0 6px;" />
    <img src="https://github.com/user-attachments/assets/f66b893b-1ba1-4247-ba36-86dd0ab95035" alt="AI Magic Fill" height="460" style="border-radius: 12px; margin: 0 6px;" />
    <img src="https://github.com/user-attachments/assets/20f1a641-1c12-4a20-9212-08080149674a" alt="Mobile Dark Mode" height="460" style="border-radius: 12px; margin: 0 6px;" />
  </p>
</div>

---

## 🤔 Why HomeStack?

Whether you want to map out the boxes in your attic, organize your kitchen pantry, keep track of collectibles, or manage your hobby supplies, HomeStack is built for you. 

Unlike heavy industrial ERPs, HomeStack is built for everyday use. **It runs smoothly on minimal hardware (low CPU and RAM usage)** and lets you catalog items just by taking a picture. You can use it as a purely digital catalog on your PC/smartphone, or go the extra mile and print QR code labels for physical tracking. 

## ✨ Features

- 🌳 **Nested Storage Hierarchy:** Organize your space logically (Rooms ➔ Shelves ➔ Cabinets ➔ Boxes ➔ Compartments). No matter how deep it goes, the breadcrumb navigation keeps it clear.
- 🤖 **AI-Powered Cataloging:** Take a picture of your item. HomeStack uses Google Gemini AI to automatically extract the name, quantity, description, and key attributes. **You can choose among all available Gemini models** depending on your needs for speed or reasoning.
- 📱 **Play Anywhere (Desktop & Mobile):** Access your inventory via your desktop web browser, or install it as a lightweight App (PWA) on your iOS/Android phone.
- 🪶 **Ultra-Lightweight:** Designed to consume very little RAM and CPU, making it perfect for hosting on older Raspberry Pis or low-end NAS devices.
- 🖨️ **Optional Label Printing:** Don't want to print? No problem, the app works flawlessly as a digital-only database. If you *do* want to print, HomeStack features a powerful modular printing engine:
  - **Web Bluetooth (BLE):** Print directly to cheap portable thermal printers (Niimbot, Fichero, etc.) right from your browser.
  - **Network Printing:** Wi-Fi/Ethernet support via TCP socket (port `9100`) for ESC/POS and TSPL protocols.
  - **System Browser Printing:** Millimeter-calibrated layout for standard desktop printing.
- 🔍 **Built-in QR Scanner:** Use your phone's camera to scan a container's QR code and instantly see what's inside.

---

## 🏗️ Architecture

```text
 💻 Desktop Browser / 📱 Mobile PWA (Vue 3)
   ├── 📷 Html5Qrcode Scanner
   └── 🖨️ Web Bluetooth (Optional Label Printing)
         │
         ▼ (Port 80 / Nginx Reverse Proxy)
 ⚙️ Backend (FastAPI / Python)
   ├── 🧠 Google Gemini AI (Selectable Models)
   ├── 🖧 Network Printers (TCP/9100)
   └── 🗄️ SQLite DB (Ultra-light storage)
```

---

## 🚀 Quick Start (Docker)

The easiest way to run HomeStack is using Docker Compose.

1. Create a `docker-compose.yml` file:

```yaml
services:
  homestack:
    image: ghcr.io/giacomocavera/homestack:latest
    container_name: homestack
    restart: unless-stopped
    ports:
      - "3000:80"
    volumes:
      - ./data:/app/data
```

2. Run the container:
```bash
docker compose up -d
```

3. Open your browser at `http://localhost:3000` (or `http://YOUR_SERVER_IP:3000`).
4. Click on the **Settings ⚙️** icon to enter your Google Gemini API Key and select your preferred model.

### ⚙️ Environment Variables (Optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google AI Studio Key (can also be set directly in the UI) | *None* |
| `DATA_DIR` | Directory inside container where the SQLite database is stored | `/app/data` |

---

## ⚠️ Important Note on Bluetooth Printing (Optional)

If you decide to use the **Web Bluetooth** feature to print labels from your smartphone or remote devices, your browser requires a secure context.
**Web Bluetooth APIs ONLY work on `localhost` or via `HTTPS`.**

If you are hosting HomeStack on a local IP (e.g., `http://192.168.1.100`), the Bluetooth connect button will silently fail or be blocked by your browser. 
**Solution:** Put HomeStack behind a reverse proxy with SSL (like Caddy, Nginx Proxy Manager, Traefik, or use Tailscale).

---

## 🛠️ Development Setup

Want to contribute or run HomeStack locally without Docker?

**1. Clone the repository**
```bash
git clone https://github.com/giacomocavera/homestack.git
cd homestack
```

**2. Setup Backend (FastAPI)**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**3. Setup Frontend (Vue 3)**
```bash
cd frontend
npm install
npm run dev
```

---

## 🗺️ Roadmap

- [x] Basic CRUD operations and hierarchical storage
- [x] Google Gemini AI integration (with model selection)
- [x] Cross-platform PWA / Desktop UI
- [x] Optional Bluetooth & Network printing
- [ ] CSV Import/Export for easy migration
- [ ] Multi-user support
- [ ] Offline caching for PWA

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/giacomocavera/homestack/issues).

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---
<div align="center">
  <i>Built with ❤️ by <a href="https://github.com/giacomocavera">Giacomo</a> for anyone who wants a tidy home and a clear mind.</i>
</div>
