# nilan2homeassistant

This repository contains Home Assistant configuration files and information how to natively integrate Nilan E-series heatpumps into Home Assistant. As I don't have EC9 with floor heating support I could not prepare temperature out to batter/floor heating. If you have EC9 and want to enhance, it should be fairly easy. Please create pull request after making configuration work.

## Hardware requirements:
- Nilan E/EC/EC9 with CTS-602 compatible controller. Control card is important one, not display.
- USB RS-485 adapter

![Architecture](https://github.com/joriws/nilan2homeassistant/blob/b7b414c79438eca80327e0e055e847442bf7b342/HA-comms.svg)

## Modbus gateway installation:
1. Install mbusd gateway software into gateway hardware; I use Raspberry Pi Zero W with Raspbian. Other Linux computer should be fine. Use mbusd instructions.
2. Copy provided mbusd-ttyUSB0.conf to /etc/mbusd/
3. Connect USB/RS-485 adapter to Nilan controller board and Raspberry's USB port. Check Nilan documentation where to connect and how.
4. Configure mbusd for start, I used systemctl service option to load on boot. Configure by changing filename and port in file and start/enable command line if your usb-port other than /dev/ttyUSB0
```
systemctl enable mbusd@ttyUSB0.service
```
5. Start mbusd
```
systemctl start mbusd@ttyUSB0.service
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

If everything works you should see following without Nilan power/energy consumption, as that is another card I decided to add to screenshot.

![Working picture-element-card](https://github.com/joriws/nilan2homeassistant/blob/b7b414c79438eca80327e0e055e847442bf7b342/NilanEC%20example.png)

## Enhancements / Todo

- It would be nice to be able to combine modbus sensors into sensor attributes. Like hotwater bottom sensor would have attribute hotwater compressor setting when compressor can turn off. There could be a lot of combining of data.
- Picture-element-card Climate - I could not make it work.
- Other HA-based setting over modbus, like set fan speed by automation or requested temperature.

### Bugs

There might be bugs on picture card or in modbus-package, please report or create pull requests.

### Known issues:

- Home assistant and mbusd have some glitches and sensors might show "Unavailable". It will go away. It might be due to multithreaded architecture of mbusd which causes queries on top of each other. Some pages suggest "slave_sensor" configuration at Home Assistant's modbus configuration.
- Raspberry might loose Wi-Fi connectivity - consult Raspbian for fixes
- MDI icon set does not have icon for fan speed 4, so fan plus was used. On my setup fan speeds 1-3 are configured.


