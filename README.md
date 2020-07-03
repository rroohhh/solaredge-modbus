# solaredge monitoring
This is a simple python script that uses the Modbus TCP to write the information available over Modbus from a SolarEdge inverter to a influxdb database.
In addition to the normal SunSpec this also supports some proprietary registers that contain for example the battery level or the grid protection limits.

(See also the documentation under `doc`).

## setup
To be able to use Modbus TCP one has to enable it. This is possible by connecting to the WiFi network created by the inverter in WiFi access mode using the password printed on the side of the inverted. Then `http://172.16.0.1` presents
one the configuration menu, where Modbus TCP (besides other things) can be enabled.

## config
The script `dump.py` can be configured using the variables at the top of the script:
```python
MODBUSIP = 'solaredge.lan'
MODBUSPORT = '1502'

INFLUXDBIP = 'localhost'
INFLUXDBPORT = 8086
INFLUXDBUSER = 'root'
INFLUXDBPASS = 'root'
INFLUXDBDB = 'pv_monitoring'
```

## installation
Executing the `dump.py` script simply writes one set of values into the specified influxdb database.
To periodically record the values one can for example use the provided `solaredge.{service,timer}` systemd units.

To use them, copy this repository to `/usr/local/solaredge`, copy `solaredeg.{service,timer}` to `/etc/systemd/system`. Then
```
# systemctl enable --now solaredge.timer
```
will make systemd execute the script every 15 seconds automatically.
