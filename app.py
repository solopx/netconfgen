import os
import logging
import ipaddress
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    make_response,
)
from jinja2 import Environment, FileSystemLoader, StrictUndefined

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")


# --- Jinja2 Filter for IP prefix to netmask conversion ---
def ip_prefix_to_netmask(prefix_length):
    """Converts a CIDR prefix (e.g., 24) to a subnet mask (e.g., 255.255.255.0)."""
    if not isinstance(prefix_length, int) or not (0 <= prefix_length <= 32):
        return "255.255.255.255"
    netmask = []
    for i in range(4):
        if prefix_length >= 8:
            netmask.append(255)
            prefix_length -= 8
        else:
            netmask.append(256 - (1 << (8 - prefix_length)))
            prefix_length = 0
    return ".".join(map(str, netmask))


# Configure Jinja2 environment for config templates
config_env = Environment(
    loader=FileSystemLoader("templates/config_templates", encoding="utf-8"),
    undefined=StrictUndefined,
    lstrip_blocks=True,
    trim_blocks=True,
)
config_env.filters["ip_prefix_to_netmask"] = ip_prefix_to_netmask


# --- Validation Functions ---
def is_valid_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_valid_prefix(prefix):
    try:
        prefix = int(prefix)
        return 0 <= prefix <= 32
    except ValueError:
        return False


def is_valid_vlan_id(vlan_id):
    try:
        vlan_id = int(vlan_id)
        return 1 <= vlan_id <= 4094
    except ValueError:
        return False


def is_valid_vlan_list(vlan_list_str):
    """
    Valida strings de VLAN: '10,20,30-40', 'all', ou ranges amplos.
    """
    if not vlan_list_str:
        return True

    # Normaliza a string para facilitar a comparação
    clean_input = vlan_list_str.strip().lower()

    # Suporte para a entrada 'all'
    if clean_input == "all":
        return True

    parts = clean_input.split(",")
    for part in parts:
        part = part.strip()
        if not part: continue # Ignora vírgulas extras (ex: "10,,20")

        if "-" in part:
            try:
                # Trata casos como "-10" ou "10-" que quebrariam o split
                segments = part.split("-")
                if len(segments) != 2:
                    return False
                
                start, end = segments
                if not (is_valid_vlan_id(start) and is_valid_vlan_id(end)):
                    return False
                
                if int(start) >= int(end): # Range invertido ou igual (ex: 40-30)
                    return False
            except ValueError:
                return False
        else:
            if not is_valid_vlan_id(part):
                return False
                
    return True


# --- Data Storage (In-memory for simplicity) ---
vlans_data = []
interfaces_data = []
config_data = {
    "hostname": "Device-Hostname",
    "snmp_community": "public",
    "ntp_server": "ntp.org",
    "syslog_server": "",
    "dns_server": "8.8.8.8",
    "default_route": {"gateway": ""},
}


# --- Routes ---
@app.route("/")
def index():
    return render_template(
        "index.html", vlans=vlans_data, interfaces=interfaces_data, config=config_data
    )


@app.route("/add_vlan", methods=["GET", "POST"])
def add_vlan():
    if request.method == "POST":
        vlan_id = request.form.get("vlan_id", "").strip()
        vlan_name = request.form.get("vlan_name", "").strip()
        ip_address = request.form.get("ip_address", "").strip()
        prefix_length = request.form.get("prefix_length", "").strip()
        description = request.form.get("description", "").strip()
        helper_addresses = request.form.get("helper_addresses", "").strip()
        no_ip_address = "no_ip_address" in request.form
        shutdown = "shutdown" in request.form

        # Validation
        errors = []
        if not vlan_id or not is_valid_vlan_id(vlan_id):
            errors.append("Invalid VLAN ID. Must be between 1-4094.")
        if not vlan_name:
            errors.append("VLAN name is required.")
        if ip_address and not is_valid_ip(ip_address):
            errors.append("Invalid IP address.")
        if prefix_length and not is_valid_prefix(prefix_length):
            errors.append("Invalid prefix length. Must be between 0-32.")
        if (ip_address and not prefix_length) or (prefix_length and not ip_address):
            errors.append("Both IP address and prefix length are required.")

        # Check for duplicate VLAN ID
        if vlan_id and any(v["id"] == int(vlan_id) for v in vlans_data):
            errors.append("VLAN ID already exists.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("vlan_form.html")

        # Process helper addresses
        helper_list = []
        if helper_addresses:
            for helper in helper_addresses.split(","):
                helper = helper.strip()
                if helper and is_valid_ip(helper):
                    helper_list.append(helper)

        # Create VLAN data
        vlan_data = {
            "id": int(vlan_id),
            "name": vlan_name,
            "ip_address": ip_address if ip_address else None,
            "prefix_length": int(prefix_length) if prefix_length else None,
            "no_ip_address": no_ip_address,
            "description": description if description else None,
            "helper_addresses": helper_list,
            "shutdown": shutdown,
        }

        vlans_data.append(vlan_data)
        flash(f"VLAN {vlan_id} added successfully!", "success")
        return redirect(url_for("index"))

    return render_template("vlan_form.html")


@app.route("/edit_vlan/<int:vlan_id>", methods=["GET", "POST"])
def edit_vlan(vlan_id):
    vlan = next((v for v in vlans_data if v["id"] == vlan_id), None)
    if not vlan:
        flash("VLAN not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        vlan_name = request.form.get("vlan_name", "").strip()
        ip_address = request.form.get("ip_address", "").strip()
        prefix_length = request.form.get("prefix_length", "").strip()
        description = request.form.get("description", "").strip()
        helper_addresses = request.form.get("helper_addresses", "").strip()
        no_ip_address = "no_ip_address" in request.form
        shutdown = "shutdown" in request.form

        # Validation
        errors = []
        if not vlan_name:
            errors.append("VLAN name is required.")
        if ip_address and not is_valid_ip(ip_address):
            errors.append("Invalid IP address.")
        if prefix_length and not is_valid_prefix(prefix_length):
            errors.append("Invalid prefix length. Must be between 0-32.")
        if (ip_address and not prefix_length) or (prefix_length and not ip_address):
            errors.append("Both IP address and prefix length are required.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("vlan_form.html", vlan=vlan, edit_mode=True)

        # Process helper addresses
        helper_list = []
        if helper_addresses:
            for helper in helper_addresses.split(","):
                helper = helper.strip()
                if helper and is_valid_ip(helper):
                    helper_list.append(helper)

        # Update VLAN data
        vlan.update(
            {
                "name": vlan_name,
                "ip_address": ip_address if ip_address else None,
                "prefix_length": int(prefix_length) if prefix_length else None,
                "no_ip_address": no_ip_address,
                "description": description if description else None,
                "helper_addresses": helper_list,
                "shutdown": shutdown,
            }
        )

        flash(f"VLAN {vlan_id} updated successfully!", "success")
        return redirect(url_for("index"))

    return render_template("vlan_form.html", vlan=vlan, edit_mode=True)


@app.route("/delete_vlan/<int:vlan_id>")
def delete_vlan(vlan_id):
    global vlans_data
    vlans_data = [v for v in vlans_data if v["id"] != vlan_id]
    flash(f"VLAN {vlan_id} deleted successfully!", "success")
    return redirect(url_for("index"))


@app.route("/add_interface", methods=["GET", "POST"])
def add_interface():
    if request.method == "POST":
        interface_name = request.form.get("interface_name", "").strip()
        is_aos_cx = "is_aos_cx" in request.form
        mode = request.form.get("mode", "").strip()
        description = request.form.get("description", "").strip()
        access_vlan = request.form.get("access_vlan", "").strip()
        voice_vlan = request.form.get("voice_vlan", "").strip()
        allowed_vlans = request.form.get("allowed_vlans", "").strip()
        portfast = "portfast" in request.form
        bpduguard = "bpduguard" in request.form
        shutdown = "shutdown" in request.form

        # Validation
        errors = []
        if not interface_name:
            errors.append("Interface name is required.")

        if not is_aos_cx:
            if not mode or mode not in ["access", "trunk"]:
                errors.append("Mode must be 'access' or 'trunk'.")

        if (
            (not is_aos_cx or mode == "access")
            and access_vlan
            and not is_valid_vlan_id(access_vlan)
        ):
            errors.append("Invalid access VLAN ID.")
        if voice_vlan and not is_valid_vlan_id(voice_vlan):
            errors.append("Invalid voice VLAN ID.")
        if (
            (not is_aos_cx or mode == "trunk")
            and allowed_vlans
            and not is_valid_vlan_list(allowed_vlans)
        ):
            errors.append("Invalid allowed VLANs format.")

        # Check for duplicate interface name
        if interface_name and any(i["name"] == interface_name for i in interfaces_data):
            errors.append("Interface name already exists.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("interface_form.html", vlans=vlans_data)

        # Create interface data
        interface_data = {
            "name": interface_name,
            "is_aos_cx": is_aos_cx,
            "aos_cx_type": request.form.get("aos_cx_type", "non-routed")
            if is_aos_cx
            else None,
            "ip_address": request.form.get("ip_address", "").strip()
            if is_aos_cx
            else None,
            "prefix_length": int(request.form.get("prefix_length", ""))
            if is_aos_cx and request.form.get("prefix_length")
            else None,
            "mode": mode if mode else None,
            "description": description if description else None,
            "access_vlan": int(access_vlan) if access_vlan else None,
            "voice_vlan": int(voice_vlan) if voice_vlan else None,
            "allowed_vlans": allowed_vlans if allowed_vlans else None,
            "portfast": portfast,
            "bpduguard": bpduguard,
            "shutdown": shutdown,
        }

        interfaces_data.append(interface_data)
        flash(f"Interface {interface_name} added successfully!", "success")
        return redirect(url_for("index"))

    return render_template("interface_form.html", vlans=vlans_data)


@app.route("/edit_interface/<path:interface_name>", methods=["GET", "POST"])
def edit_interface(interface_name):
    interface = next((i for i in interfaces_data if i["name"] == interface_name), None)
    if not interface:
        flash("Interface not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        new_name = request.form.get("name", "").strip()
        is_aos_cx = "is_aos_cx" in request.form
        mode = request.form.get("mode", "").strip()
        description = request.form.get("description", "").strip()
        access_vlan = request.form.get("access_vlan", "").strip()
        voice_vlan = request.form.get("voice_vlan", "").strip()
        allowed_vlans = request.form.get("allowed_vlans", "").strip()
        portfast = "portfast" in request.form
        bpduguard = "bpduguard" in request.form
        shutdown = "shutdown" in request.form

        # Validation
        errors = []
        if not is_aos_cx:
            if not mode or mode not in ["access", "trunk"]:
                errors.append("Mode must be 'access' or 'trunk'.")

        if not new_name:
            errors.append("Interface name is required.")

        if (
            (not is_aos_cx or mode == "access")
            and access_vlan
            and not is_valid_vlan_id(access_vlan)
        ):
            errors.append("Invalid access VLAN ID.")
        if voice_vlan and not is_valid_vlan_id(voice_vlan):
            errors.append("Invalid voice VLAN ID.")
        if (
            (not is_aos_cx or mode == "trunk")
            and allowed_vlans
            and not is_valid_vlan_list(allowed_vlans)
        ):
            errors.append("Invalid allowed VLANs format.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "interface_form.html",
                interface=interface,
                vlans=vlans_data,
                edit_mode=True,
            )

        # Update interface data
        interface.update(
            {
                "is_aos_cx": is_aos_cx,
                "aos_cx_type": request.form.get("aos_cx_type", "non-routed")
                if is_aos_cx
                else None,
                "ip_address": request.form.get("ip_address", "").strip()
                if is_aos_cx
                else None,
                "prefix_length": int(request.form.get("prefix_length", ""))
                if is_aos_cx and request.form.get("prefix_length")
                else None,
                "name": new_name,
                "mode": mode if mode else None,
                "description": description if description else None,
                "access_vlan": int(access_vlan) if access_vlan else None,
                "voice_vlan": int(voice_vlan) if voice_vlan else None,
                "allowed_vlans": allowed_vlans if allowed_vlans else None,
                "portfast": portfast,
                "bpduguard": bpduguard,
                "shutdown": shutdown,
            }
        )

        flash(f"Interface {interface_name} updated successfully!", "success")
        return redirect(url_for("index"))

    return render_template(
        "interface_form.html", interface=interface, vlans=vlans_data, edit_mode=True
    )


@app.route("/delete_interface/<path:interface_name>")
def delete_interface(interface_name):
    global interfaces_data
    interfaces_data = [i for i in interfaces_data if i["name"] != interface_name]
    flash(f"Interface {interface_name} deleted successfully!", "success")
    return redirect(url_for("index"))


@app.route("/update_config", methods=["POST"])
def update_config():
    hostname = request.form.get("hostname", "").strip()
    snmp_community = request.form.get("snmp_community", "").strip()
    ntp_server = request.form.get("ntp_server", "").strip()
    syslog_server = request.form.get("syslog_server", "").strip()
    dns_server = request.form.get("dns_server", "").strip()
    gateway = request.form.get("gateway", "").strip()

    if hostname:
        config_data["hostname"] = hostname

    config_data["snmp_community"] = snmp_community
    config_data["ntp_server"] = ntp_server
    config_data["syslog_server"] = syslog_server
    config_data["dns_server"] = dns_server

    if gateway and is_valid_ip(gateway):
        config_data["default_route"]["gateway"] = gateway
    elif gateway:
        flash("Invalid gateway IP address.", "error")
        return redirect(url_for("index"))

    flash("Configuration updated successfully!", "success")
    return redirect(url_for("index"))


@app.route("/generate_config/<platform>")
def generate_config(platform):
    if platform not in ["ios_xe", "nx_os", "hpe_aruba", "aos_cx"]:
        flash("Invalid platform selected.", "error")
        return redirect(url_for("index"))

    try:
        template = config_env.get_template(f"{platform}_config.j2")

        # Prepare data for template
        template_data = {
            "hostname": config_data["hostname"],
            "snmp_community": config_data.get("snmp_community", ""),
            "ntp_server": config_data.get("ntp_server", ""),
            "syslog_server": config_data.get("syslog_server", ""),
            "dns_server": config_data.get("dns_server", ""),
            "vlans": vlans_data,
            "interfaces": interfaces_data,
            "default_route": config_data["default_route"]
            if config_data["default_route"]["gateway"]
            else None,
        }

        config_output = template.render(**template_data)

        # Create response with proper headers for file download
        response = make_response(config_output)
        response.headers["Content-Type"] = "text/plain"
        response.headers["Content-Disposition"] = (
            f"attachment; filename={config_data['hostname']}_{platform}_config.txt"
        )

        return response

    except Exception as e:
        flash(f"Error generating configuration: {str(e)}", "error")
        return redirect(url_for("index"))


@app.route("/preview_config/<platform>")
def preview_config(platform):
    if platform not in ["ios_xe", "nx_os", "hpe_aruba", "aos_cx"]:
        return jsonify({"error": "Invalid platform selected."}), 400

    try:
        template = config_env.get_template(f"{platform}_config.j2")

        # Prepare data for template
        template_data = {
            "hostname": config_data["hostname"],
            "snmp_community": config_data.get("snmp_community", ""),
            "ntp_server": config_data.get("ntp_server", ""),
            "syslog_server": config_data.get("syslog_server", ""),
            "dns_server": config_data.get("dns_server", ""),
            "vlans": vlans_data,
            "interfaces": interfaces_data,
            "default_route": config_data["default_route"]
            if config_data["default_route"]["gateway"]
            else None,
        }

        config_output = template.render(**template_data)
        return jsonify({"config": config_output})

    except Exception as e:
        return jsonify({"error": f"Error generating configuration: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
