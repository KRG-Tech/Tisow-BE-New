import json
import re
import time

import meterbus
import serial


def key_maker(key_data: dict) -> str:
    unit_enh = "unit_enh"
    key = " ".join(key_data["type"].split(".")[1].lower().split("_"))
    if unit_enh in key_data:
        key = (
            key
            + " "
            + " ".join(key_data[unit_enh].split(".")[1].lower().split("_")[::-1])
        )
    if key == "date time general":
        key = "time point"
    return key


def get_serial_mbus_data(addr, com_port, baud_rate) -> dict | bool:
    try:
        ser = serial.Serial(com_port, baud_rate, 8, "E", 1, timeout=5)
        try:
            meterbus.send_ping_frame(ser, addr)
            time.sleep(0.5)
            frame = meterbus.load(meterbus.recv_frame(ser, 1))
            assert isinstance(frame, meterbus.TelegramACK)

            meterbus.send_request_frame(ser, addr)
            time.sleep(0.5)
            frame = meterbus.load(meterbus.recv_frame(ser, meterbus.FRAME_DATA_LENGTH))
            assert isinstance(frame, meterbus.TelegramLong)
            data = frame.to_JSON()
            dict_conv = json.loads(data)
            identity = re.sub(
                r"[0x,\s]", "", dict_conv["body"]["header"]["identification"]
            )
            data = dict_conv["body"]["records"]
            tags = []
            for val in enumerate(data):
                index = val[0] + 1
                raw_data = val[1]
                key = key_maker(raw_data)
                if key in tags:
                    key = f"{key} {index}"
                tags += (key,)
            return {"device_id": identity, "tag_list": tags}
        except Exception as err:
            print(str(err))
            return False
        finally:
            if ser.is_open:
                ser.close()
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return False
