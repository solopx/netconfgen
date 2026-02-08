# Network Configuration Generator

A simple web tool that generates switch configurations for Cisco and HPE/Aruba devices. Enter your VLANs and interfaces through a web form, and get ready-to-use configurations.

## What It Does

- **Cisco IOS-XE** - For Catalyst switches
- **Cisco NX-OS** - For Nexus switches  
- **HPE/Aruba Comware** - For legacy HPE and Comware switches
- **Aruba AOS-CX** - For next-gen Aruba switches (supports L2 and L3 interfaces)
- **VLAN Management** - Add VLANs with IPs and names
- **Interface Config** - Set up access and trunk ports with range support (e.g., `GigabitEthernet0/1-24`)
- **Global Management** - Configure NTP, Syslog, DNS, and SNMP community strings
- **Voice VLANs** - Proper syntax for each platform including AOS-CX trunk-based voice

## Quick Start

### Run
```bash
git clone https://github.com/solopx/netconfgen.git
cd netconfgen.git
pip install -r requirements.txt
export SESSION_SECRET="any-random-string"
python main.py
```

Then open `http://localhost:5000`

## How to Use

1. **Global Settings** - Set your hostname, management servers (NTP, DNS, Syslog), and SNMP community
2. **Add VLANs** - Set VLAN ID, name, and optional IP address for SVIs
3. **Configure Interfaces** - Choose access or trunk mode, and use range notation for bulk config
4. **Generate Config** - Pick your switch type and get the configuration
5. **Copy & Use** - Copy the config and paste it into your switch

## Screenshots

![](./assets/screenshot-01.png)

![](./assets/screenshot-02.png)

![](./assets/screenshot-03.png)

## Notes

- **AOS-CX Support**: Includes specific `routing` vs `no routing` logic for Layer 3/Layer 2 ports.
- **Port Ranges**: Supports standard dash notation for configuring multiple ports at once.
- **Voice VLANs**: Automatically handles platform-specific voice commands (e.g., `switchport voice vlan` on Cisco vs `voice vlan enable` on Comware).
- Always test configurations in a lab first.
- The tool stores settings in memory (resets when you restart).

## License

MIT License - use it however you want.
