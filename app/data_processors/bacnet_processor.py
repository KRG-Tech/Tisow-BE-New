import json
import time
import BAC0
from BAC0.core.io.IOExceptions import InitializationError
from app.common_functions.helper_functions import (
    read_bacnet_prop,
    ws_send_message,
    replace_inf_with_string,
    set_device_status,
    device_data_former,
)
from app.settings import DB
from app.sql_schemas.models import Devices, RawData


def get_raw_value(bacnet, device_config):
    raw_data = []
    for tag in device_config["tags"]:
        tag, instant_id, mac = tag["tag"], tag["id"], device_config["mac"]
        tag_val = read_bacnet_prop(bacnet, mac, tag, instant_id, "presentValue")
        if not tag_val:
            tag_val = 0
        raw_data += (
            {
                "tag": tag,
                "id": instant_id,
                "value": replace_inf_with_string(tag_val),
                "timestamp": int(time.time()),
            },
        )
    return raw_data


def bacnet_data_acquisition(device_id, loop):
    flag = True
    while flag:
        db = None
        bacnet_network = None
        device_data = dict()
        raw_tags_value = list()
        try:
            db = next(DB())
            device = db.query(Devices).get({"id": device_id})
            try:
                device_data = device_data_former(device)
                raw_tags_value = [
                    {"tag": tag["tag"], "id": tag["id"], "value": 0}
                    for tag in device_data["tags"]
                ]
                if device.is_deleted:
                    websocket_msg = json.dumps(
                        {
                            "data": raw_tags_value,
                            "status": "inActive",
                            "mac": device_data["mac"],
                            "timestamp": int(time.time()),
                        }
                    )
                    ws_send_message(
                        topic=device_data["mac"], message=websocket_msg, loop=loop
                    )
                    flag = False
                bacnet_network = BAC0.connect(
                    ip=device_data["host"]["host"], port=device_data["host"]["port"]
                )
                raw_tags_value = get_raw_value(bacnet_network, device_data)
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
                if db.is_active:
                    db.close()
                bacnet_network.disconnect()
            except InitializationError:
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
                (
                    bacnet_network.disconnect()
                    if bacnet_network
                    else bacnet_data_acquisition(device_data, loop)
                )
            time.sleep(device_data.get("frequency", 60))
        except Exception as err:
            set_device_status(device_data, "inActive")
            if db.is_active:
                db.close()
            time.sleep(30)
            (
                bacnet_network.disconnect()
                if bacnet_network
                else bacnet_data_acquisition(device_data, loop)
            )
