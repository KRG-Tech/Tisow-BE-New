import asyncio
import json
import threading
import time
from datetime import datetime

from sqlalchemy import func

from app.settings import DB, TOPICS, WS_LIVE_TOPIC
from app.sql_schemas.models import RawData, Devices, DeviceHosts

topics = TOPICS
topic = WS_LIVE_TOPIC


def users_data_former(val):
    return {
        "id": val.id,
        "first_name": val.first_name,
        "second_name": val.second_name,
        "email": val.email,
        "is_admin": val.is_admin,
        "created_on": datetime.fromtimestamp(val.timestamp).strftime(
            "%d-%m-%Y %H:%M:%S"
        ),
        "role": val.role,
        "rule": val.rule,
    }


def host_device_status(devices):
    try:
        host_status = any(
            True if device.status == "active" and not device.is_deleted else False
            for device in devices
        )
        return "active" if host_status else "inActive"
    except Exception as err:
        print(f"failed to get host status: {str(err)}")
        return "inActive"


def hosts_data_former(val):
    return {
        "id": val.id,
        "type": val.type,
        "host": val.host,
        "host_name": val.host_name,
        "port": val.port,
        "device_type": "host",
        "other_conf": val.other_conf,
        "status": host_device_status(val.devices),
    }


def device_data_former(val):
    return {
        "id": val.id,
        "mac": val.mac,
        "device_name": val.device_name,
        "instant_id": val.instant_id,
        "description": val.description,
        "frequency": val.frequency,
        "tags": val.tags,
        "other_conf": val.other_conf,
        "device_type": "device",
        "host": hosts_data_former(val.host),
        "status": val.status,
    }


def widget_data_former(val):
    return {
        "id": val.id,
        "device": device_data_former(val.device),
        "from_time": val.from_time,
        "to_time": val.to_time,
        "tags": val.tags,
        "widget_type": val.widget_type,
        "name": val.widget_name,
    }


def history_data_former(val, protocol):
    if protocol == "bacnet":
        return {f"{col['tag']}-{col['id']}": col["value"] for col in val}
    else:
        return {col["tag"]: col["value"] for col in val}


def dashboards_data_former(val):
    return {"id": val.id, "name": val.dashboard_name}


def read_bacnet_prop(network, device_mac, object_type, instant_id, property_name):
    try:
        raw_props = network.read(
            f"{device_mac} {object_type} {instant_id} {property_name}", timeout=5000
        )
        return raw_props
    except Exception as e:
        return []


async def send_message(topic: str, message: str):
    if topic in topics:
        for connection in topics[topic]:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error sending message: {e}")


def ws_send_message(topic: str, message: str, loop):
    try:
        loop.run_until_complete(send_message(topic=topic, message=message))
    except Exception as err:
        print(str(err))


def get_raw_data(device_id, topic, loop):
    try:
        db = next(DB())
        raw_data = (
            db.query(RawData)
            .join(Devices)
            .filter(Devices.id == device_id, ~Devices.is_deleted)
            .order_by(RawData.timestamp.desc())
            .first()
        )
        if raw_data:
            message = {
                "data": raw_data.tags,
                "status": "inActive",
                "mac": raw_data.device.mac,
                "timestamp": raw_data.timestamp,
            }
        else:
            device = db.query(Devices).get({"id": device_id})
            device = device_data_former(device)
            raw_tags_value = [
                {
                    "tag": tag["tag"],
                    "id": tag["id"],
                    "value": 0,
                    "timestamp": int(time.time()),
                }
                for tag in device.get("tags", [])
            ]
            message = {
                "data": raw_tags_value,
                "status": "inActive",
                "mac": device.get("mac", ""),
                "timestamp": int(time.time()),
            }

        websocket_msg = json.dumps(message)
        ws_send_message(topic=topic, message=websocket_msg, loop=loop)
    except Exception as err:
        print(str(err))


def send_ws_message_wth_thread(topic: str, message: str):
    def send_msg(loop, topic, msg):
        ws_send_message(topic=topic, message=msg, loop=loop)

    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=send_msg, args=(loop, topic, message))
    thread.start()


def replace_inf_with_string(data):
    if isinstance(data, float) and (data == float("inf") or data == float("-inf")):
        return "inf" if data == float("inf") else "-inf"
    elif not isinstance(data, int) or data < 0 or data > 255:
        return str(data)
    return data


def set_device_status(device, status):
    try:
        db = next(DB())
        device = db.query(Devices).get({"id": device["id"]})
        device.status = status
        (db.add(device), db.commit())
    except Exception as err:
        print(f"failed to set device status: {device['device_name']}")


def is_host_exists(query, payload):
    if payload["type"] == "bacnet":
        return query.where(DeviceHosts.host == payload["host"]).where(
            ~DeviceHosts.is_deleted
        )
    elif payload["type"] == "mbus":
        if payload["other_conf"].get("connection_type") == "serial":
            return query.where(
                func.json_extract(DeviceHosts.other_conf, "$.com_port")
                == payload["other_conf"]["com_port"]
            ).where(~DeviceHosts.is_deleted)
        else:
            return query.where(DeviceHosts.host == payload["host"]).where(
                ~DeviceHosts.is_deleted
            )
    elif payload["type"] == "modbus":
        if payload["other_conf"].get("connection_type") == "rtu":
            return query.where(
                func.json_extract(DeviceHosts.other_conf, "$.com_port")
                == payload["other_conf"]["com_port"]
            ).where(~DeviceHosts.is_deleted)
        else:
            return query.where(DeviceHosts.host == payload["host"]).where(
                ~DeviceHosts.is_deleted
            )
    return query
