import json
import time
from pymodbus.client import ModbusSerialClient as ModbusClient
from pymodbus.exceptions import ModbusException
from app.common_functions.helper_functions import (
    device_data_former,
    ws_send_message,
    set_device_status,
)
from app.settings import DB
from app.sql_schemas.models import Devices, RawData


def modbus_data_acquisition(device_id, loop):
    def send_status_update(data, status):
        ws_send_message(
            topic=device_data["mac"],
            message=json.dumps(
                {
                    "data": data,
                    "status": status,
                    "mac": device_data["mac"],
                    "timestamp": int(time.time()),
                }
            ),
            loop=loop,
        )
        set_device_status(device_data, status)

    while True:
        db = next(DB())
        device = db.query(Devices).get({"id": device_id})
        device_data = device_data_former(device)

        if device.is_deleted:
            send_status_update([], "inActive")
            db.close()
            break

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
            host_conf = device_data["host"]["other_conf"]
            client = ModbusClient(
                port=host_conf["com_port"],
                baudrate=host_conf["baud_rate"],
                timeout=1,
                stopbits=host_conf["stop_bits"],
                bytesize=host_conf["byte_size"],
                parity=host_conf["parity"],
            )

            if not client.connect():
                print("Failed to connect to Modbus device")
                send_status_update(raw_tags_value, "inActive")
                db.close()
                time.sleep(30)
                continue

            for tag in raw_tags_value:
                try:
                    result = client.read_holding_registers(
                        address=tag["id"], count=1, slave=int(device_data["mac"])
                    )
                    if not result.isError():
                        tag["value"] = result.registers[0]
                except ModbusException as e:
                    print(f"Modbus exception while reading register {tag['id']}: {e}")
                except Exception as err:
                    print(f"Error reading register {tag['id']}")

            device_status = any(tag["value"] != 0 for tag in raw_tags_value)
            status = "active" if device_status else "inActive"
            if device_status:
                db.add(RawData(device_id=device_data["id"], tags=raw_tags_value))
                db.commit()

            send_status_update(raw_tags_value, status)
            client.close()

        except Exception as e:
            print(f"Unexpected error: {e}")
            send_status_update(raw_tags_value, "inActive")
            time.sleep(30)

        finally:
            if db.is_active:
                db.close()

        time.sleep(device_data["frequency"])
