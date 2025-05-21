# 🖧 UniFi MAC Address Search Web Tool

Created by **Chota Mulenga**, this is a Flask web application that allows users to log into a UniFi Controller, search for a MAC address across all sites, and view where the MAC is found. The app uses asynchronous programming to ensure fast and efficient lookups even on large-scale UniFi setups.

---

## 🚀 Features

- Login interface for UniFi Controller authentication
- Asynchronous MAC address search across multiple sites
- Session-based login handling
- Performance logging and graceful timeout handling

---

## 🔧 Requirements

Install Python packages:

```bash
pip install -r requirements.txt

----------------------------------------------------------------------------------------------------------

🛠️ Setup Instructions

Clone this repository or download the files.
Edit the UniFi Controller URL
Open the main app file (e.g., app.py) and locate the following line:


UNIFI_CONTROLLER = ""  # Enter your controller URL here

Replace it with your actual controller URL, e.g.:
UNIFI_CONTROLLER = "https://192.168.1.1:8443"


Run the App

On the terminal:

python app.py

The server will start locally (by default at http://127.0.0.1:5000).

Open your browser
Visit: http://127.0.0.1:5000
Log in using your UniFi Controller credentials and search for any MAC address.

🧠 Notes
Ensure your controller allows local login over HTTPS and doesn't block requests from unknown origins.
For cloud-hosted UniFi controllers (e.g., Ubiquiti HostiFi), ensure you use the correct URL and port.

🤝 Contributing
Feel free to fork and improve this tool. Pull requests and suggestions are welcome!


