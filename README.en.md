
![Python Badge](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff&style=for-the-badge) ![Flask Badge](https://img.shields.io/badge/Flask-3BABC3?logo=flask&logoColor=fff&style=for-the-badge) ![Jinja Badge](https://img.shields.io/badge/Jinja-7E0C1B?logo=jinja&logoColor=fff&style=for-the-badge)

# Network Configuration Generator

NetConfGen is a tool designed to simplify the work of anyone configuring devices via CLI.

Whether you are a network engineer, a test analyst, or a student working with different vendors, this is the fastest way to configure your devices without typos or headaches.

Instead of wasting time memorizing commands for every brand, you simply enter the desired settings into the interface, and the app transforms them into ready-to-use configuration files.

This way, you can focus on the project while the app takes care of generating the correct code for each device.

## Features

### Multi-Platform Support

- **Cisco IOS-XE**
- **Cisco NX-OS**
- **HPE/Aruba Comware**
- **Aruba AOS-CX**

### Core Capabilities

- **VLAN Management**: Add, edit, delete, and duplicate VLANs data and voice VLANs.
- **Interface Management**:
  - **Access & Trunk Modes**: Standard switching port configurations.
  - **Port Ranges**: Bulk configure interfaces using standard notation (e.g., `1/1-48`, `Giga0/1-24)`).
  - **L3 Routing**: Toggle AOS-CX ports between `routing` and `no routing` modes.
  - **Duplicate**: Clone any interface with one click to speed up repetitive configurations.
- **Voice VLANs**: Automated platform-specific syntax (e.g., `switchport voice vlan` vs hybrid port modes).
- **Port-Channel / LAG**: Configure link aggregation groups with LACP (active/passive) or static mode.
  - IOS-XE: `Port-channel` + `channel-group mode`
  - NX-OS: `port-channel` + `channel-group mode`
  - HPE/Aruba: `Bridge-Aggregation` + `port link-aggregation group`
  - AOS-CX: `lag` + member interface binding
- **Static Routes**: Add multiple static routes (network/prefix/gateway) beyond the default route.
- **Global Services**
  - **NTP Servers** for time synchronization.
  - **Syslog Hosts** for centralized logging.
  - **DNS Servers** for name resolution.
  - **SNMP Communities** for monitoring.
  - **Default Gateway** for management routing.

## Screenshots

<details>
<summary> Clique here to see the screenshots </summary>
<br>

![](./assets/screenshot-01.png)

![](./assets/screenshot-02.png)

![](./assets/screenshot-03.png)

</details>

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
4. Run the main python app:
   ```bash
   python main.py
   ```
5. Open your web browser and navigate to:
   ```bash
   http://localhost:5000
   ```
   
## How it Works

1. **Global Configuration**: Set your device hostname, management servers, and default gateway.
2. **Static Routes**: Add additional static routes beyond the default route.
3. **VLANs**: Create your Layer 2 broadcast domains and Layer 3 interfaces.
4. **Port Channels**: Define LAG/EtherChannel groups and their member interfaces.
5. **Map Interfaces**: Assign ports to VLANs or configure high-bandwidth trunks.
6. **Generate & Export**: Select your target platform and download the CLI-ready configuration.

## Important Notes

- **Safety First**: Always review and validate generated configurations in a lab environment before deploying to production.

- **In-Memory Storage**: For security and simplicity, this version stores data in volatile memory. Configurations are cleared when the server restarts.

## License
This project is licensed under the MIT License - feel free to modify and use it for your needs.
