import copy
import secrets
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

logging.basicConfig(level=logging.WARNING)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)


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


def ip_prefix_to_wildcard(prefix):
    mask_int = (0xFFFFFFFF >> int(prefix)) & 0xFFFFFFFF
    return str(ipaddress.IPv4Address(mask_int))


config_env = Environment(
    loader=FileSystemLoader("templates/config_templates", encoding="utf-8"),
    undefined=StrictUndefined,
    lstrip_blocks=True,
    trim_blocks=True,
)
config_env.filters["ip_prefix_to_netmask"] = ip_prefix_to_netmask
config_env.filters["ip_prefix_to_wildcard"] = ip_prefix_to_wildcard


def is_valid_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_valid_hostname(h):
    if is_valid_ip(h):
        return True
    if not h or len(h) > 253:
        return False
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")
    return all(
        label
        and len(label) <= 63
        and not label.startswith("-")
        and not label.endswith("-")
        and all(c in allowed for c in label)
        for label in h.split(".")
    )


def is_valid_snmp_community(community):
    if not community:
        return False
    invalid_chars = {" ", '"', "'", "\n", "\t", "\r"}
    return not any(c in community for c in invalid_chars)


def is_safe_text(text):
    return all(ord(c) >= 32 for c in text)


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
    if not vlan_list_str:
        return True

    clean_input = vlan_list_str.strip().lower()

    if clean_input == "all":
        return True

    parts = clean_input.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            try:
                segments = part.split("-")
                if len(segments) != 2:
                    return False

                start, end = segments
                if not (is_valid_vlan_id(start) and is_valid_vlan_id(end)):
                    return False

                if int(start) >= int(end):
                    return False
            except ValueError:
                return False
        else:
            if not is_valid_vlan_id(part):
                return False

    return True


vlans_data = []
interfaces_data = []
static_routes_data = []
port_channels_data = []
acls_data = []
config_data = {
    "hostname": "Device-Hostname",
    "snmp_community": "public",
    "ntp_server": "ntp.org",
    "syslog_server": "",
    "dns_server": "8.8.8.8",
    "default_route": {"gateway": ""},
}


@app.route("/")
def index():
    return render_template(
        "index.html",
        vlans=vlans_data,
        interfaces=interfaces_data,
        config=config_data,
        static_routes=static_routes_data,
        port_channels=port_channels_data,
        acls=acls_data,
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

        errors = []
        if not vlan_id or not is_valid_vlan_id(vlan_id):
            errors.append("Invalid VLAN ID. Must be between 1-4094.")
        if not vlan_name:
            errors.append("VLAN name is required.")
        elif not is_safe_text(vlan_name):
            errors.append("VLAN name cannot contain control characters.")
        if description and not is_safe_text(description):
            errors.append("Description cannot contain control characters.")
        if ip_address and not is_valid_ip(ip_address):
            errors.append("Invalid IP address.")
        if prefix_length and not is_valid_prefix(prefix_length):
            errors.append("Invalid prefix length. Must be between 0-32.")
        if (ip_address and not prefix_length) or (prefix_length and not ip_address):
            errors.append("Both IP address and prefix length are required.")
        if vlan_id and any(v["id"] == int(vlan_id) for v in vlans_data):
            errors.append("VLAN ID already exists.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("vlan_form.html")

        helper_list = []
        invalid_helpers = []
        if helper_addresses:
            for helper in helper_addresses.split(","):
                helper = helper.strip()
                if not helper:
                    continue
                if is_valid_ip(helper):
                    helper_list.append(helper)
                else:
                    invalid_helpers.append(helper)
        if invalid_helpers:
            flash(f"Invalid helper address(es) ignored: {', '.join(invalid_helpers)}", "warning")

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
        raw_vlan_id = request.form.get("vlan_id", "").strip()
        vlan_name = request.form.get("vlan_name", "").strip()
        ip_address = request.form.get("ip_address", "").strip()
        prefix_length = request.form.get("prefix_length", "").strip()
        description = request.form.get("description", "").strip()
        helper_addresses = request.form.get("helper_addresses", "").strip()
        no_ip_address = "no_ip_address" in request.form
        shutdown = "shutdown" in request.form

        errors = []
        if not raw_vlan_id or not is_valid_vlan_id(raw_vlan_id):
            errors.append("Invalid VLAN ID. Must be between 1-4094.")
        elif int(raw_vlan_id) != vlan_id and any(v["id"] == int(raw_vlan_id) for v in vlans_data):
            errors.append("VLAN ID already exists.")
        if not vlan_name:
            errors.append("VLAN name is required.")
        elif not is_safe_text(vlan_name):
            errors.append("VLAN name cannot contain control characters.")
        if description and not is_safe_text(description):
            errors.append("Description cannot contain control characters.")
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

        helper_list = []
        invalid_helpers = []
        if helper_addresses:
            for helper in helper_addresses.split(","):
                helper = helper.strip()
                if not helper:
                    continue
                if is_valid_ip(helper):
                    helper_list.append(helper)
                else:
                    invalid_helpers.append(helper)
        if invalid_helpers:
            flash(f"Invalid helper address(es) ignored: {', '.join(invalid_helpers)}", "warning")

        vlan.update(
            {
                "id": int(raw_vlan_id),
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
    vlans_data[:] = [v for v in vlans_data if v["id"] != vlan_id]
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

        errors = []
        if not interface_name:
            errors.append("Interface name is required.")
        elif not is_safe_text(interface_name):
            errors.append("Interface name cannot contain control characters.")
        if description and not is_safe_text(description):
            errors.append("Description cannot contain control characters.")

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

        if is_aos_cx:
            aos_cx_type = request.form.get("aos_cx_type", "non-routed")
            ip_address = request.form.get("ip_address", "").strip()
            ip_prefix = request.form.get("prefix_length", "").strip()
            if aos_cx_type == "routed":
                if not ip_address:
                    errors.append("IP address is required for AOS-CX routed interface.")
                elif not is_valid_ip(ip_address):
                    errors.append("Invalid AOS-CX IP address.")
                if not ip_prefix:
                    errors.append("Prefix length is required for AOS-CX routed interface.")

        if interface_name and any(i["name"] == interface_name for i in interfaces_data):
            errors.append("Interface name already exists.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("interface_form.html", vlans=vlans_data)

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

        errors = []
        if not is_aos_cx:
            if not mode or mode not in ["access", "trunk"]:
                errors.append("Mode must be 'access' or 'trunk'.")

        if not new_name:
            errors.append("Interface name is required.")
        elif not is_safe_text(new_name):
            errors.append("Interface name cannot contain control characters.")
        if description and not is_safe_text(description):
            errors.append("Description cannot contain control characters.")

        if is_aos_cx:
            edit_aos_cx_type = request.form.get("aos_cx_type", "non-routed")
            edit_ip_address = request.form.get("ip_address", "").strip()
            edit_ip_prefix = request.form.get("prefix_length", "").strip()
            if edit_aos_cx_type == "routed":
                if not edit_ip_address:
                    errors.append("IP address is required for AOS-CX routed interface.")
                elif not is_valid_ip(edit_ip_address):
                    errors.append("Invalid AOS-CX IP address.")
                if not edit_ip_prefix:
                    errors.append("Prefix length is required for AOS-CX routed interface.")

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
    interfaces_data[:] = [i for i in interfaces_data if i["name"] != interface_name]
    flash(f"Interface {interface_name} deleted successfully!", "success")
    return redirect(url_for("index"))


@app.route("/duplicate_vlan/<int:vlan_id>")
def duplicate_vlan(vlan_id):
    vlan = next((v for v in vlans_data if v["id"] == vlan_id), None)
    if not vlan:
        flash("VLAN not found.", "error")
        return redirect(url_for("index"))
    existing_ids = {v["id"] for v in vlans_data}
    new_id = vlan_id + 1
    while new_id in existing_ids and new_id <= 4094:
        new_id += 1
    if new_id > 4094:
        flash("No available VLAN ID to duplicate into.", "error")
        return redirect(url_for("index"))
    new_vlan = copy.deepcopy(vlan)
    new_vlan["id"] = new_id
    new_vlan["name"] = vlan["name"] + "-copy"
    vlans_data.append(new_vlan)
    flash(f"VLAN {vlan_id} duplicated as VLAN {new_id}.", "success")
    return redirect(url_for("edit_vlan", vlan_id=new_id))


@app.route("/duplicate_interface/<path:interface_name>")
def duplicate_interface(interface_name):
    interface = next((i for i in interfaces_data if i["name"] == interface_name), None)
    if not interface:
        flash("Interface not found.", "error")
        return redirect(url_for("index"))
    existing_names = {i["name"] for i in interfaces_data}
    new_name = interface_name + "-copy"
    counter = 1
    while new_name in existing_names:
        new_name = f"{interface_name}-copy{counter}"
        counter += 1
    new_interface = copy.deepcopy(interface)
    new_interface["name"] = new_name
    interfaces_data.append(new_interface)
    flash(f"Interface '{interface_name}' duplicated as '{new_name}'.", "success")
    return redirect(url_for("edit_interface", interface_name=new_name))


@app.route("/add_static_route", methods=["GET", "POST"])
def add_static_route():
    if request.method == "POST":
        network = request.form.get("network", "").strip()
        prefix = request.form.get("prefix", "").strip()
        gateway = request.form.get("gateway", "").strip()
        errors = []
        if not network or not is_valid_ip(network):
            errors.append("Invalid network address.")
        if not prefix or not is_valid_prefix(prefix):
            errors.append("Invalid prefix length.")
        if not gateway or not is_valid_ip(gateway):
            errors.append("Invalid gateway address.")
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("static_route_form.html")
        static_routes_data.append({
            "network": network,
            "prefix": int(prefix),
            "gateway": gateway,
        })
        flash("Static route added.", "success")
        return redirect(url_for("index"))
    return render_template("static_route_form.html")


@app.route("/delete_static_route/<int:route_idx>")
def delete_static_route(route_idx):
    if 0 <= route_idx < len(static_routes_data):
        static_routes_data.pop(route_idx)
        flash("Static route deleted.", "success")
    return redirect(url_for("index"))


@app.route("/edit_static_route/<int:route_idx>", methods=["GET", "POST"])
def edit_static_route(route_idx):
    if route_idx < 0 or route_idx >= len(static_routes_data):
        flash("Static route not found.", "error")
        return redirect(url_for("index"))
    route = static_routes_data[route_idx]
    if request.method == "POST":
        network = request.form.get("network", "").strip()
        prefix = request.form.get("prefix", "").strip()
        gateway = request.form.get("gateway", "").strip()
        errors = []
        if not network or not is_valid_ip(network):
            errors.append("Invalid network address.")
        if not prefix or not is_valid_prefix(prefix):
            errors.append("Invalid prefix length.")
        if not gateway or not is_valid_ip(gateway):
            errors.append("Invalid gateway address.")
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("static_route_form.html", route=route, route_idx=route_idx, edit_mode=True)
        static_routes_data[route_idx] = {
            "network": network,
            "prefix": int(prefix),
            "gateway": gateway,
        }
        flash("Static route updated.", "success")
        return redirect(url_for("index"))
    return render_template("static_route_form.html", route=route, route_idx=route_idx, edit_mode=True)


@app.route("/duplicate_static_route/<int:route_idx>")
def duplicate_static_route(route_idx):
    if route_idx < 0 or route_idx >= len(static_routes_data):
        flash("Static route not found.", "error")
        return redirect(url_for("index"))
    new_route = copy.deepcopy(static_routes_data[route_idx])
    static_routes_data.append(new_route)
    new_idx = len(static_routes_data) - 1
    flash("Static route duplicated.", "success")
    return redirect(url_for("edit_static_route", route_idx=new_idx))


@app.route("/add_port_channel", methods=["GET", "POST"])
def add_port_channel():
    if request.method == "POST":
        pc_id_raw = request.form.get("pc_id", "").strip()
        description = request.form.get("description", "").strip()
        lacp_mode = request.form.get("lacp_mode", "active").strip()
        member_interfaces_raw = request.form.get("member_interfaces", "").strip()
        switchport_mode = request.form.get("switchport_mode", "").strip()
        access_vlan = request.form.get("access_vlan", "").strip()
        allowed_vlans = request.form.get("allowed_vlans", "").strip()
        shutdown = "shutdown" in request.form
        errors = []
        pc_id = None
        if not pc_id_raw:
            errors.append("Port-channel ID is required.")
        else:
            try:
                pc_id = int(pc_id_raw)
                if not (1 <= pc_id <= 999):
                    errors.append("Port-channel ID must be between 1 and 999.")
            except ValueError:
                errors.append("Invalid Port-channel ID.")
        if pc_id and any(p["id"] == pc_id for p in port_channels_data):
            errors.append("Port-channel ID already exists.")
        if description and not is_safe_text(description):
            errors.append("Description cannot contain control characters.")
        if not member_interfaces_raw:
            errors.append("At least one member interface is required.")
        else:
            members = [m.strip() for m in member_interfaces_raw.split(",") if m.strip()]
            if not members:
                errors.append("At least one member interface is required.")
            elif any(not is_safe_text(m) for m in members):
                errors.append("Member interface names cannot contain control characters.")
        if not switchport_mode or switchport_mode not in ["access", "trunk"]:
            errors.append("Mode must be 'access' or 'trunk'.")
        if lacp_mode not in ["active", "passive", "on"]:
            errors.append("Invalid LACP mode.")
        if switchport_mode == "access" and access_vlan and not is_valid_vlan_id(access_vlan):
            errors.append("Invalid access VLAN ID.")
        if switchport_mode == "trunk" and allowed_vlans and not is_valid_vlan_list(allowed_vlans):
            errors.append("Invalid allowed VLANs format.")
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("port_channel_form.html", vlans=vlans_data)
        members = [m.strip() for m in member_interfaces_raw.split(",") if m.strip()]
        port_channels_data.append({
            "id": pc_id,
            "description": description if description else None,
            "lacp_mode": lacp_mode,
            "member_interfaces": members,
            "switchport_mode": switchport_mode,
            "access_vlan": int(access_vlan) if access_vlan else None,
            "allowed_vlans": allowed_vlans if allowed_vlans else None,
            "shutdown": shutdown,
        })
        flash(f"Port-channel {pc_id} added successfully!", "success")
        return redirect(url_for("index"))
    return render_template("port_channel_form.html", vlans=vlans_data)


@app.route("/edit_port_channel/<int:pc_id>", methods=["GET", "POST"])
def edit_port_channel(pc_id):
    pc = next((p for p in port_channels_data if p["id"] == pc_id), None)
    if not pc:
        flash("Port-channel not found.", "error")
        return redirect(url_for("index"))
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        lacp_mode = request.form.get("lacp_mode", "active").strip()
        member_interfaces_raw = request.form.get("member_interfaces", "").strip()
        switchport_mode = request.form.get("switchport_mode", "").strip()
        access_vlan = request.form.get("access_vlan", "").strip()
        allowed_vlans = request.form.get("allowed_vlans", "").strip()
        shutdown = "shutdown" in request.form
        errors = []
        if description and not is_safe_text(description):
            errors.append("Description cannot contain control characters.")
        if not member_interfaces_raw:
            errors.append("At least one member interface is required.")
        else:
            members = [m.strip() for m in member_interfaces_raw.split(",") if m.strip()]
            if not members:
                errors.append("At least one member interface is required.")
            elif any(not is_safe_text(m) for m in members):
                errors.append("Member interface names cannot contain control characters.")
        if not switchport_mode or switchport_mode not in ["access", "trunk"]:
            errors.append("Mode must be 'access' or 'trunk'.")
        if lacp_mode not in ["active", "passive", "on"]:
            errors.append("Invalid LACP mode.")
        if switchport_mode == "access" and access_vlan and not is_valid_vlan_id(access_vlan):
            errors.append("Invalid access VLAN ID.")
        if switchport_mode == "trunk" and allowed_vlans and not is_valid_vlan_list(allowed_vlans):
            errors.append("Invalid allowed VLANs format.")
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("port_channel_form.html", pc=pc, vlans=vlans_data, edit_mode=True)
        members = [m.strip() for m in member_interfaces_raw.split(",") if m.strip()]
        pc.update({
            "description": description if description else None,
            "lacp_mode": lacp_mode,
            "member_interfaces": members,
            "switchport_mode": switchport_mode,
            "access_vlan": int(access_vlan) if access_vlan else None,
            "allowed_vlans": allowed_vlans if allowed_vlans else None,
            "shutdown": shutdown,
        })
        flash(f"Port-channel {pc_id} updated successfully!", "success")
        return redirect(url_for("index"))
    return render_template("port_channel_form.html", pc=pc, vlans=vlans_data, edit_mode=True)


@app.route("/delete_port_channel/<int:pc_id>")
def delete_port_channel(pc_id):
    port_channels_data[:] = [p for p in port_channels_data if p["id"] != pc_id]
    flash(f"Port-channel {pc_id} deleted.", "success")
    return redirect(url_for("index"))


def _parse_acl_entries(form):
    entries = []
    i = 0
    while f"entry_action_{i}" in form:
        action = form.get(f"entry_action_{i}", "").strip()
        if not action:
            i += 1
            continue
        sequence_raw = form.get(f"entry_sequence_{i}", "").strip()
        sequence = int(sequence_raw) if sequence_raw.isdigit() else None
        source_prefix_raw = form.get(f"entry_source_prefix_{i}", "").strip()
        dest_prefix_raw = form.get(f"entry_dest_prefix_{i}", "").strip()
        entries.append({
            "sequence": sequence,
            "action": action,
            "protocol": form.get(f"entry_protocol_{i}", "ip").strip() or "ip",
            "source_type": form.get(f"entry_source_type_{i}", "any").strip(),
            "source": form.get(f"entry_source_{i}", "").strip() or None,
            "source_prefix": int(source_prefix_raw) if source_prefix_raw.isdigit() else None,
            "dest_type": form.get(f"entry_dest_type_{i}", "any").strip(),
            "dest": form.get(f"entry_dest_{i}", "").strip() or None,
            "dest_prefix": int(dest_prefix_raw) if dest_prefix_raw.isdigit() else None,
            "remark": form.get(f"entry_remark_{i}", "").strip() or None,
        })
        i += 1
    return entries


def _validate_acl_form(form, existing_idx=None):
    errors = []
    name = form.get("name", "").strip()
    acl_type = form.get("type", "").strip()
    description = form.get("description", "").strip()
    apply_interface = form.get("apply_interface", "").strip()
    apply_direction = form.get("apply_direction", "").strip()

    if not name:
        errors.append("ACL name is required.")
    elif " " in name:
        errors.append("ACL name cannot contain spaces.")
    elif not is_safe_text(name):
        errors.append("ACL name cannot contain control characters.")
    if acl_type not in ["standard", "extended"]:
        errors.append("ACL type must be 'standard' or 'extended'.")
    if description and not is_safe_text(description):
        errors.append("ACL description cannot contain control characters.")
    if apply_interface and not is_safe_text(apply_interface):
        errors.append("Apply interface cannot contain control characters.")
    if apply_direction and apply_direction not in ["inbound", "outbound"]:
        errors.append("Direction must be 'inbound' or 'outbound'.")

    entries = _parse_acl_entries(form)
    if not entries:
        errors.append("At least one ACL entry is required.")
    if entries:
        has_seq = [e["sequence"] is not None for e in entries]
        if any(has_seq) and not all(has_seq):
            errors.append("Sequence numbers must be defined for all entries or for none.")
        seq_values = [e["sequence"] for e in entries if e["sequence"] is not None]
        if len(seq_values) != len(set(seq_values)):
            errors.append("Duplicate sequence numbers are not allowed.")
        invalid_seqs = [e["sequence"] for e in entries if e["sequence"] is not None and not (1 <= e["sequence"] <= 4294967295)]
        if invalid_seqs:
            errors.append("Sequence numbers must be between 1 and 4294967295.")
        entry_signatures = [
            (e["action"], e["protocol"], e["source_type"], e["source"], e["source_prefix"],
             e["dest_type"], e["dest"], e["dest_prefix"])
            for e in entries
        ]
        if len(entry_signatures) != len(set(entry_signatures)):
            errors.append("Duplicate entries are not allowed within the same ACL.")
    for i, entry in enumerate(entries):
        if entry["action"] not in ["permit", "deny"]:
            errors.append(f"Entry {i+1}: action must be 'permit' or 'deny'.")
        if entry["remark"] and not is_safe_text(entry["remark"]):
            errors.append(f"Entry {i+1}: remark cannot contain control characters.")
        if entry["source_type"] == "network":
            if not entry["source"] or not is_valid_ip(entry["source"]):
                errors.append(f"Entry {i+1}: invalid source network address.")
            if entry["source_prefix"] is None or not is_valid_prefix(entry["source_prefix"]):
                errors.append(f"Entry {i+1}: invalid source prefix length.")
        elif entry["source_type"] == "host":
            if not entry["source"] or not is_valid_ip(entry["source"]):
                errors.append(f"Entry {i+1}: invalid source host address.")
        if acl_type == "extended":
            if entry["dest_type"] == "network":
                if not entry["dest"] or not is_valid_ip(entry["dest"]):
                    errors.append(f"Entry {i+1}: invalid destination network address.")
                if entry["dest_prefix"] is None or not is_valid_prefix(entry["dest_prefix"]):
                    errors.append(f"Entry {i+1}: invalid destination prefix length.")
            elif entry["dest_type"] == "host":
                if not entry["dest"] or not is_valid_ip(entry["dest"]):
                    errors.append(f"Entry {i+1}: invalid destination host address.")
    return errors, name, acl_type, entries


@app.route("/add_acl", methods=["GET", "POST"])
def add_acl():
    if request.method == "POST":
        errors, name, acl_type, entries = _validate_acl_form(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            temp_acl = {
                "name": name,
                "type": acl_type,
                "description": request.form.get("description", "").strip(),
                "apply_interface": request.form.get("apply_interface", "").strip() or None,
                "apply_direction": request.form.get("apply_direction", "inbound"),
                "entries": entries,
            }
            return render_template("acl_form.html", acl=temp_acl)
        description = request.form.get("description", "").strip()
        apply_interface = request.form.get("apply_interface", "").strip()
        apply_direction = request.form.get("apply_direction", "inbound").strip()
        acls_data.append({
            "name": name,
            "type": acl_type,
            "description": description if description else None,
            "apply_interface": apply_interface if apply_interface else None,
            "apply_direction": apply_direction if apply_interface else None,
            "entries": entries,
        })
        flash(f"ACL '{name}' added successfully!", "success")
        return redirect(url_for("index"))
    return render_template("acl_form.html")


@app.route("/edit_acl/<int:idx>", methods=["GET", "POST"])
def edit_acl(idx):
    if idx < 0 or idx >= len(acls_data):
        flash("ACL not found.", "error")
        return redirect(url_for("index"))
    acl = acls_data[idx]
    if request.method == "POST":
        errors, name, acl_type, entries = _validate_acl_form(request.form, existing_idx=idx)
        if errors:
            for error in errors:
                flash(error, "error")
            temp_acl = {
                "name": name,
                "type": acl_type,
                "description": request.form.get("description", "").strip(),
                "apply_interface": request.form.get("apply_interface", "").strip() or None,
                "apply_direction": request.form.get("apply_direction", "inbound"),
                "entries": entries,
            }
            return render_template("acl_form.html", acl=temp_acl, idx=idx, edit_mode=True)
        description = request.form.get("description", "").strip()
        apply_interface = request.form.get("apply_interface", "").strip()
        apply_direction = request.form.get("apply_direction", "inbound").strip()
        acl.update({
            "name": name,
            "type": acl_type,
            "description": description if description else None,
            "apply_interface": apply_interface if apply_interface else None,
            "apply_direction": apply_direction if apply_interface else None,
            "entries": entries,
        })
        flash(f"ACL '{name}' updated successfully!", "success")
        return redirect(url_for("index"))
    return render_template("acl_form.html", acl=acl, idx=idx, edit_mode=True)


@app.route("/delete_acl/<int:idx>")
def delete_acl(idx):
    if 0 <= idx < len(acls_data):
        name = acls_data[idx]["name"]
        acls_data.pop(idx)
        flash(f"ACL '{name}' deleted.", "success")
    return redirect(url_for("index"))


@app.route("/duplicate_acl/<int:idx>")
def duplicate_acl(idx):
    if idx < 0 or idx >= len(acls_data):
        flash("ACL not found.", "error")
        return redirect(url_for("index"))
    new_acl = copy.deepcopy(acls_data[idx])
    new_acl["name"] = new_acl["name"] + "-copy"
    acls_data.append(new_acl)
    new_idx = len(acls_data) - 1
    flash(f"ACL duplicated.", "success")
    return redirect(url_for("edit_acl", idx=new_idx))


@app.route("/update_config", methods=["POST"])
def update_config():
    hostname = request.form.get("hostname", "").strip()
    snmp_community = request.form.get("snmp_community", "").strip()
    ntp_server = request.form.get("ntp_server", "").strip()
    syslog_server = request.form.get("syslog_server", "").strip()
    dns_server = request.form.get("dns_server", "").strip()
    gateway = request.form.get("gateway", "").strip()

    errors = []

    if not hostname:
        errors.append("Hostname is required.")
    elif not is_safe_text(hostname):
        errors.append("Hostname cannot contain control characters.")

    if snmp_community and not is_valid_snmp_community(snmp_community):
        errors.append("SNMP community must not contain spaces or quotes.")

    if ntp_server and not is_valid_hostname(ntp_server):
        errors.append("Invalid NTP server address.")

    if syslog_server and not is_valid_hostname(syslog_server):
        errors.append("Invalid Syslog server address.")

    if dns_server and not is_valid_ip(dns_server):
        errors.append("Invalid DNS server IP address.")

    if gateway and not is_valid_ip(gateway):
        errors.append("Invalid default gateway IP address.")

    if errors:
        for error in errors:
            flash(error, "error")
        return redirect(url_for("index"))

    config_data["hostname"] = hostname
    config_data["snmp_community"] = snmp_community
    config_data["ntp_server"] = ntp_server
    config_data["syslog_server"] = syslog_server
    config_data["dns_server"] = dns_server

    if gateway:
        config_data["default_route"]["gateway"] = gateway

    flash("Configuration updated successfully!", "success")
    return redirect(url_for("index"))


@app.route("/generate_config/<platform>")
def generate_config(platform):
    if platform not in ["ios_xe", "nx_os", "hpe_aruba", "aos_cx"]:
        flash("Invalid platform selected.", "error")
        return redirect(url_for("index"))

    try:
        template = config_env.get_template(f"{platform}_config.j2")

        template_data = {
            "hostname": config_data["hostname"],
            "snmp_community": config_data.get("snmp_community", ""),
            "ntp_server": config_data.get("ntp_server", ""),
            "syslog_server": config_data.get("syslog_server", ""),
            "dns_server": config_data.get("dns_server", ""),
            "vlans": vlans_data,
            "interfaces": interfaces_data,
            "static_routes": static_routes_data,
            "port_channels": port_channels_data,
            "default_route": config_data["default_route"]
            if config_data["default_route"]["gateway"]
            else None,
        }

        config_output = template.render(**template_data)

        if acls_data:
            acl_template = config_env.get_template(f"acl/{platform}_acl.j2")
            config_output += "\n" + acl_template.render(acls=acls_data)

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

        template_data = {
            "hostname": config_data["hostname"],
            "snmp_community": config_data.get("snmp_community", ""),
            "ntp_server": config_data.get("ntp_server", ""),
            "syslog_server": config_data.get("syslog_server", ""),
            "dns_server": config_data.get("dns_server", ""),
            "vlans": vlans_data,
            "interfaces": interfaces_data,
            "static_routes": static_routes_data,
            "port_channels": port_channels_data,
            "default_route": config_data["default_route"]
            if config_data["default_route"]["gateway"]
            else None,
        }

        config_output = template.render(**template_data)

        if acls_data:
            acl_template = config_env.get_template(f"acl/{platform}_acl.j2")
            config_output += "\n" + acl_template.render(acls=acls_data)

        return jsonify({"config": config_output})

    except Exception as e:
        return jsonify({"error": f"Error generating configuration: {str(e)}"}), 500
