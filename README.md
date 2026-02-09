
![Python Badge](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff&style=for-the-badge) ![Flask Badge](https://img.shields.io/badge/Flask-3BABC3?logo=flask&logoColor=fff&style=for-the-badge) ![Jinja Badge](https://img.shields.io/badge/Jinja-7E0C1B?logo=jinja&logoColor=fff&style=for-the-badge)

# Network Configuration Generator

A professional web-based tool for network engineers and administrators to rapidly generate  configuration files for Cisco and HPE/Aruba devices.

Bridge the gap between planning and deployment with a simple, validated interface.

## Features

### Multi-Platform Support

- **Cisco IOS-XE** - Optimized for Catalyst switching platforms.
- **Cisco NX-OS** - Tailored for Nexus data center switching.
- **HPE/Aruba Comware** - Support for legacy HPE and Comware-based switches.
- **Aruba AOS-CX** - Modern syntax support including advanced L2/L3 port logic.

### Core Capabilities

- **VLAN Management**: Add, edit, and delete VLANs with optional SVI (IP) configuration.
- **Interface Flexibility**:
  - **Access & Trunk Modes**: Standard switching port configurations.
  - **Port Ranges**: Bulk configure interfaces using standard notation (e.g., `1/1-48`).
  - **L3 Routing**: Toggle AOS-CX ports between `routing` and `no routing` modes.
- **Voice VLANs**: Automated platform-specific syntax (e.g., `switchport voice vlan` vs hybrid port modes).
- **Global Services**: One-click configuration for:
  - **NTP Servers** for time synchronization.
  - **Syslog Hosts** for centralized logging.
  - **DNS Servers** for name resolution.
  - **SNMP Communities** for monitoring.

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/solopx/netconfgen.git
   ```
2. Browse to the directory:
   ```bash
   cd netconfgen
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set your session secret and run:
   ```bash
   export SESSION_SECRET="your-secure-key"
   python main.py
   ```
5. Open your web browser and navigate to `http://localhost:5000`

## How it Works

1. **Initialize Global Configuration**: Set your device hostname and management servers.
2. **Define VLANs**: Create your Layer 2 broadcast domains and Layer 3 interfaces.
3. **Map Interfaces**: Assign ports to VLANs or configure high-bandwidth trunks.
4. **Generate & Export**: Select your target platform and download the CLI-ready configuration.

## Screenshots

![](./assets/screenshot-01.png)

![](./assets/screenshot-02.png)

![](./assets/screenshot-03.png)


## Important Notes

- **Safety First**: Always review and validate generated configurations in a lab environment before deploying to production.

- **IP Validation**: Built-in validation ensures IP addresses and netmasks follow standard networking protocols.

- **In-Memory Storage**: For security and simplicity, this version stores data in volatile memory. Configurations are cleared when the server restarts.


## License
This project is licensed under the MIT License - feel free to modify and use it for your networking needs.