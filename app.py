from flask import Flask,request, render_template_string, redirect
import subprocess

app = Flask(__name__)

wifi_device = "wlan0"

def GetAvailableNetworks():
    html = ""
    try:
        result = subprocess.check_output(["nmcli", "--colors", "no", "-m", "multiline", "--get-value", "SSID", "dev", "wifi", "list", "ifname", wifi_device])
        ssids_list = result.decode().split('\n')

        html += f"""
            <h1>Wifi Control</h1>
            <form action="/submit" method="post">
                <label for="ssid">Choose a WiFi network:</label>
                <select name="ssid" id="ssid">
            """
        for ssid in ssids_list:
            only_ssid = ssid.removeprefix("SSID:")
            if len(only_ssid) > 0:
                html += f"""
                <option value="{only_ssid}">{only_ssid}</option>
                """
        html += f"""
                </select>
                <p/>
                <label for="password">Password: <input name="password"/></label>
                <p/>
                <input type="submit" value="Connect">
            </form>
            """

    except subprocess.CalledProcessError as e:
        html += f"""
            <h1>No Wifi Device Found</h1>
            """

    return html

def GetVPNLocations():
    html = ""
    try:
        result = subprocess.check_output(["ls", "/etc/openvpn"])
        vpnLocations = result.decode().split('\n')

        html += f"""
            <form action="/ConnectToVPN" method="post">
                <label for="location">Choose a VPN location:</label>
                <select name="VPNLocation" id="VPNLocation">
            """
        html += f"""
            <option value="NONE">NONE</option>
            """
        for location in vpnLocations:
            if len(location) > 0 and ".ovpn" in location:
                html += f"""
                <option value="{location}">{location}</option>
                """
        html += f"""
            </select>
            <p/>
            <input type="submit" value="Connect">
            <p/>
            </form>
            """
    except subprocess.CalledProcessError as e:
        html += f"""
            <h1>No VPN Locations Found</h1>
            <p/>
            """
    return html

@app.route('/data_wifistatus')
def data_wifistatus():
    wifi_status = subprocess.check_output(["nmcli", "dev", "wifi", "list"])
    wifi_status = wifi_status.decode()
    tokens = wifi_status.split("\n")
    result = ""
    for line in tokens:
        if '*' in line:
            result += "<p/>"
            result += line
    return result

@app.route('/data_temperature')
def data_temperature():
    temp = subprocess.check_output(["vcgencmd", "measure_temp"])
    temp = temp.decode().strip('\n')
    return temp

@app.route('/data_ip_address')
def data_ip_address():
    ipAddress = subprocess.check_output(["curl", "ifconfig.me"])#
    ipAddress = ipAddress.decode().strip('\n')
    return "IP: " + ipAddress

@app.route('/pistats', methods=['GET', 'POST'])
def pistats(): 
    arm_mem = subprocess.check_output(["vcgencmd", "get_mem", "arm"])
    arm_mem = arm_mem.decode().strip('\n')
    gpu_mem = subprocess.check_output(["vcgencmd", "get_mem", "gpu"])
    gpu_mem = gpu_mem.decode().strip('\n')

    html = f"""
    {arm_mem}
    <p/>
    {gpu_mem}
    <p/>
    """

    html += render_template_string("""
    <span id="time"><span>
    <script type="text/javascript">
    var time_span = document.getElementById("time");
    function updater() {
    fetch('/data_temperature')
    .then(response => response.text())
    .then(text => (time_span.innerHTML = text));  // update page with new data
    }
    setInterval(updater, 5000);  // run `updater()` every 1000ms (1s)
    </script>
    <p/>
    """)

    html += render_template_string("""
    <span id="wifi"><span>
    <script type="text/javascript">
    var wifi_data = document.getElementById("wifi");
    function updater() {
    fetch('/data_wifistatus')
    .then(response => response.text())
    .then(text => (wifi_data.innerHTML = text));  // update page with new data
    }
    setInterval(updater, 10000);  // run `updater()` every 1000ms (1s)
    </script>
    <p/>
    """)

    html += render_template_string("""
    <span id="ip_address"><span>
    <script type="text/javascript">
    var address = document.getElementById("ip_address");
    function updater() {
    fetch('/data_ip_address')
    .then(response => response.text())
    .then(text => (address.innerHTML = text));  // update page with new data
    }
    setInterval(updater, 10000);  // run `updater()` every 1000ms (1s)
    </script>
    <p/>
    """)

    html += GetVPNLocations()
    return html

@app.route('/')
def index():
    dropdowndisplay = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <title>Wifi Control</title>
        </head>
        <body>
        """
    dropdowndisplay += GetAvailableNetworks()
    dropdowndisplay += f"""
            <form action="/changebssid" method="post">
                <p/>
                <label for="bssid">New BSSID: <input name="bssid"/></label>
                <p/>
                <input type="submit" value="Set BSSID">
                <p/>
            </form>
            <form action="/shutdown" method="post">
                <input type="submit" value="Shutdown">
            </form>
            <form action="/reboot" method="post">
                <p/>
                <input type="submit" value="Reboot">
            </form>
            <p/>
            <a href="http://travelpi.local:8096">Jellyfin 8096</a>
            <p/>
            <a href="http://travelpi.local/pistats">Stats</a>
        </body>
    </html>
    """
    return dropdowndisplay

@app.route('/ConnectToVPN',methods=['POST'])
def ConnectToVPN():
    location = request.form['VPNLocation']
    if request.method == 'POST':
        if location != 'NONE':
            ovpnFile = "/etc/openvpn/{}".format(location)
            connection_command = ['sudo', '-b', 'openvpn', '--config', ovpnFile, '--auth-user-pass', '/etc/openvpn/con.txt']
        else:
            connection_command = ['sudo', '-b', 'killall', 'openvpn']

    result = subprocess.Popen(connection_command)

    return redirect(("/pistats"), code=307)

@app.route('/shutdown',methods=['POST'])
def shutdown():
    if request.method == 'POST':
        result = subprocess.run(["sudo", "shutdown", "now"], capture_output=False)
    return "Shutdown!"

@app.route('/reboot',methods=['POST'])
def reboot():
    if request.method == 'POST':
        result = subprocess.run(["sudo", "reboot"], capture_output=False)
    return "Reboot!"

@app.route('/changebssid',methods=['POST'])
def changebssid():
    if request.method == 'POST':
        bssid = request.form['bssid']
        #16f99539-6b26-48eb-9466-709854cb5dd4
        #9482dc26-d9e9-40df-b1bd-b3595b63463b
        result = subprocess.run(["sudo", "nmcli", "connection", "modify", "9b2eb23f-874b-46cb-8348-c6330dc4ec49", "802-11-wireless.ssid", bssid], capture_output=True)
        if result.stderr:
            return "Error: failed to connect to rename wifi network: <i>%s</i>" % result.stderr.decode()
        elif result.stdout:
            return "Success: <i>%s</i>" % result.stdout.decode()
        return "Error: failed to connect."

@app.route('/submit',methods=['POST'])
def submit():
    if request.method == 'POST':
        print(*list(request.form.keys()), sep = ", ")
        ssid = request.form['ssid']
        password = request.form['password']
        connection_command = ["nmcli", "--colors", "no", "device", "wifi", "connect", ssid, "ifname", wifi_device]
        if len(password) > 0:
          connection_command.append("password")
          connection_command.append(password)
        result = subprocess.run(connection_command, capture_output=True)
        if result.stderr:
            return "Error: failed to connect to wifi network: <i>%s</i>" % result.stderr.decode()
        elif result.stdout:
            return "Success: <i>%s</i>" % result.stdout.decode()
        return "Error: failed to connect."


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
