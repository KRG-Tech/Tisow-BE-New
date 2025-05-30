import re
import time
import serial
import meterbus
import json
from app.common_functions.helper_functions import (
    set_device_status,
    ws_send_message,
    device_data_former,
)
from app.common_functions.mbus_functions import key_maker
from app.settings import DB
from app.sql_schemas.models import Devices, RawData


def mbus_data_acquisition(device_id, loop):
    flag = True
    while flag:
        db = next(DB())
        device = db.query(Devices).get({"id": device_id})
        device_data = device_data_former(device)
        raw_tags_value = [
            {
                "tag": tag["tag"],
                "id": tag["id"],
                "value": 0,
                "timestamp": int(time.time()),
            }
            for tag in device_data["tags"]
        ]
        try:
            if device.is_deleted:
                websocket_msg = json.dumps(
                    {
                        "data": [],
                        "status": "inActive",
                        "mac": device_data["mac"],
                        "timestamp": int(time.time()),
                    }
                )
                ws_send_message(
                    topic=device_data["mac"], message=websocket_msg, loop=loop
                )
                flag = False
                if db.is_active:
                    db.close()
            try:
                host_conf = device_data["host"]["other_conf"]
                device_conf = device_data["other_conf"]
                ser = serial.Serial(
                    host_conf["com_port"],
                    device_conf["baud_rate"],
                    8,
                    "E",
                    1,
                    timeout=5,
                )
                try:
                    meterbus.send_ping_frame(ser, device_conf["address"])
                    time.sleep(0.5)
                    frame = meterbus.load(meterbus.recv_frame(ser, 1))
                    assert isinstance(frame, meterbus.TelegramACK)

                    meterbus.send_request_frame(ser, device_conf["address"])
                    time.sleep(0.5)
                    frame = meterbus.load(
                        meterbus.recv_frame(ser, meterbus.FRAME_DATA_LENGTH)
                    )
                    assert isinstance(frame, meterbus.TelegramLong)
                    data = frame.to_JSON()
                    dict_conv = json.loads(data)
                    identity = re.sub(
                        r"[0x,\s]", "", dict_conv["body"]["header"]["identification"]
                    )
                    data = dict_conv["body"]["records"]
                    tags = dict()
                    tags_data = list()
                    selected_tags = [i["tag"] for i in raw_tags_value]
                    for val in enumerate(data):
                        index = val[0] + 1
                        raw_data = val[1]
                        key = key_maker(raw_data)
                        if key in tags:
                            key = f"{key} {index}"
                        if key in selected_tags:
                            tags[key] = raw_data["value"]
                            tags_data += (
                                {
                                    "tag": key,
                                    "id": identity,
                                    "value": tags[key],
                                    "timestamp": int(time.time()),
                                },
                            )
                            raw_tags_value = tags_data
                    device_status = any(
                        [True if tag["value"] != 0 else False for tag in raw_tags_value]
                    )
                    status = "inActive"
                    if device_status:
                        raw_data = RawData(
                            device_id=device_data["id"],
                            tags=raw_tags_value,
                        )
                        db.add(raw_data)
                        db.commit()
                        status = "active"
                    set_device_status(device_data, status)
                    websocket_msg = json.dumps(
                        {
                            "data": raw_tags_value,
                            "status": status,
                            "mac": device_data["mac"],
                            "timestamp": int(time.time()),
                        }
                    )
                    ws_send_message(
                        topic=device_data["mac"], message=websocket_msg, loop=loop
                    )
                    ser.close()
                    if db.is_active:
                        db.close()
                except Exception as err:
                    if db.is_active:
                        db.close()
                    set_device_status(device_data, "inActive")
                    time.sleep(30)
                    mbus_data_acquisition(device_data["id"], loop)
                finally:
                    if ser.is_open:
                        ser.close()
            except serial.SerialException as e:
                if db.is_active:
                    db.close()
                set_device_status(device_data, "inActive")
                time.sleep(30)
                mbus_data_acquisition(device_data["id"], loop)
                print(f"Error opening serial port: {e}")

        except Exception:
            if db.is_active:
                db.close()
            set_device_status(device_data, "inActive")
            ws_send_message(
                topic=device_data["mac"],
                message=json.dumps(
                    {
                        "data": raw_tags_value,
                        "status": "inActive",
                        "mac": device_data["mac"],
                        "timestamp": int(time.time()),
                    }
                ),
                loop=loop,
            )
            time.sleep(30)
            mbus_data_acquisition(device_data["id"], loop)
        time.sleep(device_data.get("frequency", 60))
