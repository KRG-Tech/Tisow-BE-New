import asyncio
import threading
from sqlalchemy import and_
from app.data_processors.bacnet_processor import bacnet_data_acquisition
from app.settings import DB
from app.sql_schemas.models import Devices, DeviceHosts


# mqtt_client = MQTT_CLIENT
# mqtt_topics = MQTT_TOPICS


def record_bacnet():
    try:
        db = next(DB())
        devices = (
            db.query(Devices)
            .join(DeviceHosts)
            .filter(and_(~Devices.is_deleted, DeviceHosts.type == "bacnet"))
            .all()
        )

        for device in devices:
            loop = asyncio.new_event_loop()
            device_thread = threading.Thread(
                target=bacnet_data_acquisition,
                args=(device.id, loop),
                name=device.device_name,
            )
            device_thread.start()
    except Exception as err:
        print(f"failed to create thread for devices: {str(err)}")
