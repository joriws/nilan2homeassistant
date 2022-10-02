# nilan2homeassistant

This repository contains Home Assistant configuration files and information how to natively integrate Nilan E-series heatpumps into Home Assistant. As I don't have EC9 with floor heating support I could not prepare temperature out to batter/floor heating. If you have EC9 and want to enhance, it should be fairly easy. Please create pull request after making configuration work.

## Hardware requirements:
- Nilan E/EC/EC9 with CTS-602 compatible controller. Control card is important one, not display.
- USB RS-485 adapter

## Modbus gateway installation:
1. Install mbusd gateway software into gateway hardware; I use Raspberry Pi Zero W with Raspbian. Other Linux computer should be fine.
2. Connect USB/RS-485 adapter to Nilan controller board and Raspberry
3. Configure mbusd, I used systemctl service option to load on boot. Configure port if other than /dev/ttyUSB0
4. Start mbusd
```
systemctl start mbusd@ttyUSB0.service
systemctl enable mbusd@ttyUSB0.service
```

## Home assistant installation:
1. Copy modbus_nilanec.yaml into /config -directory
2. Modify modbus_nilanec.yaml -file with your mbusd gateway IP-address
3. Copy NilanEC.svg into /config/www -directory
4. Add configuration lines under homeassistant: -tag
```
homeassistant:
  customize: !include customize.yaml
  packages:
    nilanec: !include modbus_nilanec.yaml
```
5. Go to developement - Check configuration files and if OK, restart
6. Edit some dashboard and create picture-element card and paste nilanec_picture-element-card.yaml into editor and save