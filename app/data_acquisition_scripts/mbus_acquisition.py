import asyncio
import threading
from sqlalchemy import and_, func
from app.data_processors.mbus_processor import mbus_data_acquisition
from app.settings import DB
from app.sql_schemas.models import Devices, DeviceHosts


def record_mbus():
    db = None
    try:
        db = next(DB())
        devices = (
            db.query(Devices)
            .join(DeviceHosts)
            .filter(
                and_(
                    ~Devices.is_deleted,
                    DeviceHosts.type == "mbus",
                    func.json_extract(DeviceHosts.other_conf, "$.connection_type")
                    == "serial",
                )
            )
            .all()
        )

        for device in devices:
            loop = asyncio.new_event_loop()
            device_thread = threading.Thread(
                target=mbus_data_acquisition,
                args=(device.id, loop),
                name=device.device_name,
            )
            device_thread.start()
        db.close()
    except Exception as err:
        print(f"failed to create thread for devices: {str(err)}")
    finally:
        db.close()
