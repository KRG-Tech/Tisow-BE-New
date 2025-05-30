import asyncio
from io import BytesIO
import threading
import BAC0
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import joinedload, Session
from starlette.responses import JSONResponse

from app.common_functions.helper_functions import (
    read_bacnet_prop,
    hosts_data_former,
    device_data_former,
    is_host_exists,
)
from app.common_functions.mbus_functions import get_serial_mbus_data
from app.common_functions.token_handler import JWTBearer
from app.data_processors.bacnet_processor import bacnet_data_acquisition
from app.data_processors.mbus_processor import mbus_data_acquisition
from app.data_processors.modbus_processor import modbus_data_acquisition
from app.pydantic_models.deviceModel import (
    AddDevice,
    DeleteHostDevice,
    GetDevices,
    EditHost,
    EditDevice,
    GetTags,
    Host,
    MbusSearch,
    BacnetSearch,
)
from starlette import status
from sqlalchemy import update, exists as rec_exists, func
from app.settings import DB
from app.sql_schemas.models import Devices, DeviceHosts
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import json


router = APIRouter()
DEVICE_HANDLERS = {
    "bacnet": bacnet_data_acquisition,
    "mbus": mbus_data_acquisition,
    "modbus": modbus_data_acquisition,
}


def new_device_added(device_id, device_name, device_type):
    try:
        loop = asyncio.new_event_loop()
        device_thread = threading.Thread(
            target=DEVICE_HANDLERS[device_type],
            args=(device_id, loop),
            name=device_name,
        )
        device_thread.start()
    except Exception as err:
        print("failed to start thread")


@router.post("/devices/search/bacnet", dependencies=[Depends(JWTBearer())])
async def search_bacnet_devices(
    payload: BacnetSearch, response: Response = None, db: Session = Depends(DB)
):
    bacnet = None
    try:
        payload = payload.model_dump()
        host_exists = db.query(
            rec_exists()
            .where(DeviceHosts.host == payload["host"])
            .where(~DeviceHosts.is_deleted)
        ).scalar()
        if (not host_exists and payload["host_add"]) or not payload["host_add"]:
            bacnet = BAC0.connect(ip=payload["host"], port=payload["port"])
            bacnet.whois()
            devices_found = bacnet.devices
            data = []
            if len(devices_found) > 0:
                for device in devices_found:
                    dev_name, dev_manufacturer, mac, dev_id = device
                    object_list = read_bacnet_prop(
                        bacnet, mac, "device", dev_id, "objectList"
                    )
                    read_name = lambda tag_obj: read_bacnet_prop(
                        bacnet, mac, tag_obj[0], tag_obj[1], "objectName"
                    )
                    object_list = [
                        {"tag_name": read_name(obj), "tag": obj[0], "id": obj[1]}
                        for obj in object_list[1:]
                    ]
                    data += (
                        {
                            "mac": mac,
                            "dev_id": dev_id,
                            "dev_name": dev_name,
                            "dev_manufacturer": dev_manufacturer,
                            "objectList": object_list,
                        },
                    )
                bacnet.disconnect()
                return {"data": data, "msg": f"Found {len(data)} devices"}
            bacnet.disconnect()
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"msg": f"Device not found"}
        else:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"msg": f"IP already exists"}
    except Exception as err:
        bacnet.disconnect()
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/devices/search/mbus", dependencies=[Depends(JWTBearer())])
async def search_mbus_devices(
    payload: MbusSearch, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = payload.model_dump()
        query = db.query(rec_exists())
        if payload.get("connection_type") == "serial" and payload["host_add"]:
            host_exists = (
                query.where(
                    func.json_extract(DeviceHosts.other_conf, "$.com_port")
                    == payload["com_port"]
                )
                .where(~DeviceHosts.is_deleted)
                .scalar()
            )
        elif payload.get("connection_type") == "serial" and not payload["host_add"]:
            host_exists = (
                query.where(
                    func.json_extract(Devices.other_conf, "$.address")
                    == payload["address"]
                )
                .where(~Devices.is_deleted)
                .scalar()
            )
        else:
            host_exists = (
                query.where(DeviceHosts.host == payload["host"])
                .where(~DeviceHosts.is_deleted)
                .scalar()
            )
        if not host_exists:
            if payload["connection_type"]:
                data = {}
                device_data = get_serial_mbus_data(
                    payload["address"], payload["com_port"], payload["baud_rate"]
                )
                if device_data:
                    object_list = [
                        {"tag_name": tag, "tag": tag, "id": tag_id}
                        for tag_id, tag in enumerate(device_data["tag_list"])
                    ]
                    data = {
                        "mac": device_data["device_id"],
                        "objectList": object_list,
                    }

                    return {
                        "data": data,
                        "msg": f"device {device_data['device_id']} found",
                    }
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {"msg": "Failed to Connect Device"}
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"msg": "Invalid Connection Type"}
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": "Host device already exists"}
    except Exception as err:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/devices/add_device", dependencies=[Depends(JWTBearer())])
async def add_device(
    payload: AddDevice, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = payload.model_dump()
        device_data = payload["device"]
        try:
            device_exists = db.query(
                rec_exists()
                .where(Devices.mac == device_data["mac"])
                .where(~Devices.is_deleted)
            ).scalar()
            if not device_exists:
                query = db.query(rec_exists())
                host_exists = is_host_exists(query, payload).scalar()
                host_id = None
                if not host_exists and not payload["host_id"]:
                    device_host = DeviceHosts(
                        type=payload["type"],
                        host=payload["host"],
                        host_name=payload["host_name"],
                        port=payload["port"],
                        other_conf=payload["other_conf"],
                    )
                    db.add(device_host)
                    db.commit()
                    host_id = device_host.id
                elif payload["host_id"]:
                    host_id = payload["host_id"]
                else:
                    response.status_code = status.HTTP_400_BAD_REQUEST
                    return {"msg": f"{payload['host']} host already exists"}
                device = Devices(
                    mac=device_data["mac"],
                    device_name=device_data["device_name"],
                    description=device_data["description"],
                    frequency=device_data["frequency"],
                    instant_id=device_data["id"],
                    tags=device_data["tags"],
                    host_id=host_id,
                    other_conf=device_data["other_conf"],
                )
                db.add(device)
                db.commit()
                new_device_added(device.id, device.device_name, payload["type"])
                return {"msg": "Device Added Successfully"}
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"msg": f"Device {device_data['mac']} already exists"}
        except Exception as err:
            db.rollback()
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"msg": f"Failed to add device: {str(err)}"}
    except Exception as err:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/devices/get_hosts", dependencies=[Depends(JWTBearer())])
async def get_hosts(response: Response = None, db: Session = Depends(DB)):
    try:
        host_list = (
            db.query(DeviceHosts)
            .filter(~DeviceHosts.is_deleted)
            .order_by(DeviceHosts.id.desc())
            .all()
        )
        data = [hosts_data_former(item) for item in host_list]
        return JSONResponse({"data": data, "msg": "Hosts found in the server"})
    except Exception as err:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/devices/delete_host_device", dependencies=[Depends(JWTBearer())])
async def delete_host_device(
    payload: DeleteHostDevice, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = payload.model_dump()
        if payload["type"] == "host":
            device_host = (
                update(DeviceHosts)
                .where(DeviceHosts.id == payload["id"])
                .values(is_deleted=True)
            )
            db.execute(device_host)

            stmt_update_devices = (
                update(Devices)
                .where(Devices.host_id == payload["id"])
                .values(is_deleted=True)
            )
            db.execute(stmt_update_devices)
        else:
            host_dev_rec = db.query(Devices).get({"id": payload["id"]})
            if host_dev_rec:
                host_dev_rec.is_deleted = True
        db.commit()

        return {
            "msg": f"Deleted {payload['type']} {payload['device_name']} Successfully"
        }
    except Exception as err:
        db.rollback()
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": f"Failed to delete {payload['type']} {payload['device_name']}"}


@router.post("/devices/get_devices", dependencies=[Depends(JWTBearer())])
async def get_devices(
    payload: GetDevices, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = payload.model_dump()
        device_list = (
            db.query(Devices)
            .join(DeviceHosts)
            .filter(DeviceHosts.id == int(payload["id"]), ~Devices.is_deleted)
            .order_by(Devices.id.desc())
            .all()
        )
        data = [device_data_former(item) for item in device_list]
        return {"data": data, "msg": "found devices"}
    except Exception as err:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/devices/edit_host", dependencies=[Depends(JWTBearer())])
async def edit_host(
    payload: EditHost, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = payload.model_dump()
        host_rec = db.query(DeviceHosts).get({"id": payload["id"]})
        if host_rec:
            for key, value in payload.items():
                if key != "id":
                    setattr(host_rec, key, value)
            db.commit()
            return {"msg": f"Host {payload['host_name']} edited successfully"}
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": f"{payload['host_name']} doesn't exists"}
    except Exception as err:
        db.rollback()
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/devices/edit_device", dependencies=[Depends(JWTBearer())])
async def edit_device(
    payload: EditDevice, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = payload.model_dump()
        device_rec = db.query(Devices).get({"id": payload["dev_id"]})
        if device_rec:
            for key, value in payload.items():
                if key != "dev_id":
                    setattr(device_rec, key, value)
            db.commit()
            db.commit()
            return {"msg": f"Device {payload['device_name']} edited successfully"}
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": f"{payload['device_name']} doesn't exists"}
    except Exception as err:
        db.rollback()
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/devices/edit_device/tags", dependencies=[Depends(JWTBearer())])
async def get_tags(
    payload: GetTags, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = payload.model_dump()
        device_rec = (
            db.query(Devices)
            .options(joinedload(Devices.host))
            .filter(Devices.id == payload["id"])
            .first()
        )
        device_rec = device_data_former(device_rec)
        host_rec = device_rec["host"]
        object_list = list()
        host, port = host_rec["host"], host_rec["port"]
        if device_rec:
            if host_rec["type"] == "bacnet":
                bacnet = BAC0.connect(ip=host, port=port)
                object_list = read_bacnet_prop(
                    bacnet,
                    device_rec["mac"],
                    "device",
                    device_rec["instant_id"],
                    "objectList",
                )
                read_name = lambda tag_obj: read_bacnet_prop(
                    bacnet, device_rec["mac"], tag_obj[0], tag_obj[1], "objectName"
                )
                object_list = [
                    {"tag_name": read_name(obj), "tag": obj[0], "id": obj[1]}
                    for obj in object_list[1:]
                ]
                bacnet.disconnect()
            elif host_rec["type"] == "mbus":
                payload = device_rec["other_conf"]
                device_data = get_serial_mbus_data(
                    payload["address"],
                    host_rec["other_conf"]["com_port"],
                    payload["baud_rate"],
                )
                if device_data:
                    object_list = [
                        {"tag_name": tag, "tag": tag, "id": tag_id}
                        for tag_id, tag in enumerate(device_data["tag_list"])
                    ]
            return {
                "data": {"tags": object_list, "dev_type": host_rec["type"]},
                "msg": "tags found",
            }
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": f"{payload['device_name']} doesn't exists"}
    except Exception as err:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/devices/host", dependencies=[Depends(JWTBearer())])
async def get_host_data(
    payload: Host, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = payload.model_dump()
        host_rec = db.query(DeviceHosts).get({"id": payload["host_id"]})
        if host_rec:
            data = hosts_data_former(host_rec)
            return {"data": data, "msg": "found host device"}
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": "No host record found"}
    except Exception as err:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from io import BytesIO
import pandas as pd
import json
import asyncio
import threading

def parse_json_safe(val):
    if pd.isna(val):
        return None
    try:
        return json.loads(val) if isinstance(val, str) else val
    except json.JSONDecodeError:
        return None

def start_device_acquisition_thread(device_id, device_name, host_type):
    loop = asyncio.new_event_loop()
    if host_type == "modbus":
        thread = threading.Thread(
            target=modbus_data_acquisition,
            args=(device_id, loop),
            name=device_name
        )
    elif host_type == "mbus":
        thread = threading.Thread(
            target=mbus_data_acquisition,
            args=(device_id, loop),
            name=device_name
        )
    else:
        print(f"Unsupported host type for acquisition: {host_type}")
        return
    thread.start()


@router.post("/upload-devices-excel/", dependencies=[Depends(JWTBearer())])
async def upload_devices_excel(file: UploadFile = File(...), db: Session = Depends(DB)):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Please upload a valid Excel file (.xlsx or .xls)")

    try:
        contents = await file.read()
        excel_data = pd.read_excel(BytesIO(contents), sheet_name=None)

        if "device_hosts" not in excel_data or "devices" not in excel_data:
            raise HTTPException(status_code=400, detail="Excel must contain 'device_hosts' and 'devices' sheets.")

        hosts_df = excel_data["device_hosts"]
        devices_df = excel_data["devices"]

        host_id_map = {}
        new_device_threads = []  # to collect (device_id, device_name, host_type)

        # Process hosts
        for _, row in hosts_df.iterrows():
            existing_host = db.query(DeviceHosts).filter_by(
                host=row["host"],
                host_name=row["host_name"],
                port=int(row["port"])
            ).first()

            if existing_host:
                existing_host.type = row["type"]
                existing_host.is_deleted = bool(row.get("is_deleted", False))
                existing_host.other_conf = parse_json_safe(row.get("other_conf")) or {}
            else:
                existing_host = DeviceHosts(
                    type=row["type"],
                    host=row["host"],
                    host_name=row["host_name"],
                    port=int(row["port"]),
                    is_deleted=bool(row.get("is_deleted", False)),
                    other_conf=parse_json_safe(row.get("other_conf")) or {}
                )
                db.add(existing_host)
                db.flush()

            host_id_map[row["id"]] = (existing_host.id, existing_host.type)

        # Process devices
        for _, row in devices_df.iterrows():
            host_entry = host_id_map.get(row["host_id"])
            if not host_entry:
                raise HTTPException(status_code=400, detail=f"Invalid host_id {row['host_id']} in devices sheet.")
            resolved_host_id, host_type = host_entry

            existing_device = db.query(Devices).filter_by(mac=row["mac"]).first()

            if existing_device:
                existing_device.device_name = row["device_name"]
                existing_device.description = row.get("description")
                existing_device.frequency = int(row["frequency"])
                existing_device.is_deleted = bool(row.get("is_deleted", False))
                existing_device.instant_id = row.get("instant_id")
                existing_device.tags = parse_json_safe(row.get("tags"))
                existing_device.status = row.get("status", "inActive")
                existing_device.other_conf = parse_json_safe(row.get("other_conf")) or {}
                existing_device.host_id = resolved_host_id
            else:
                new_device = Devices(
                    mac=row["mac"],
                    device_name=row["device_name"],
                    description=row.get("description"),
                    frequency=int(row["frequency"]),
                    is_deleted=bool(row.get("is_deleted", False)),
                    instant_id=row.get("instant_id"),
                    tags=parse_json_safe(row.get("tags")),
                    status=row.get("status", "inActive"),
                    other_conf=parse_json_safe(row.get("other_conf")) or {},
                    host_id=resolved_host_id
                )
                db.add(new_device)
                db.flush()
                new_device_threads.append((new_device.id, new_device.device_name, host_type))

        db.commit()

        # Start threads after commit
        for device_id, device_name, host_type in new_device_threads:
            start_device_acquisition_thread(device_id, device_name, host_type)

        return {
            "message": "Upload successful. Hosts and devices were updated or inserted as needed."
        }

    except SQLAlchemyError as db_err:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


