import asyncio
import json
import threading
import uvicorn
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from fastapi.responses import JSONResponse
from app.common_functions.helper_functions import get_raw_data
from app.data_acquisition_scripts.bacnet_acquisition import record_bacnet
from app.data_acquisition_scripts.mbus_acquisition import record_mbus
from app.data_acquisition_scripts.modbus_acquisition import record_modbus
from app.routers import users, devices, dashboard
from app.settings import AppConfig, DB, TOPICS, WS_LIVE_TOPIC
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.sql_schemas.models import Users


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins; use specific origins in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods; use specific methods in production
    allow_headers=["*"],  # Allows all headers; use specific headers in production
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error = exc.errors()[0]
    return JSONResponse(
        status_code=400,
        content={"field": error["loc"][1], "msg": f"{error['msg']}: {error['loc'][1]}"},
    )


prefix = "/controller"
app.include_router(users.router, prefix=prefix)
app.include_router(devices.router, prefix=prefix)
app.include_router(dashboard.router, prefix=prefix)

Configs = AppConfig()
topics = TOPICS
ws_topic_live = WS_LIVE_TOPIC
db = next(DB())


@app.websocket("/ws/live_data/{topic}")
async def websocket_endpoint(websocket: WebSocket, topic: str):
    await websocket.accept()
    if topic not in topics:
        topics[topic] = []

    topics[topic].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            if data and (data := json.loads(data)) and data["msg"] == "GetLiveData":
                loop = asyncio.new_event_loop()
                thread = threading.Thread(
                    target=get_raw_data, args=(data["id"], topic, loop)
                )
                thread.start()
    except WebSocketDisconnect:
        topics[topic].remove(websocket)
        if not topics[topic]:
            del topics[topic]


try:
    if db.query(Users).count() == 0:
        admin_config = Configs.admin_conf()
        admin_col = {
            "first_name": admin_config["username"],
            "email": str(admin_config["email"]),
            "password": str(admin_config["password"]),
            "is_admin": True,
            "role": "Admin",
            "rule": "write",
        }
        admin = Users(**admin_col)
        db.add(admin)
        db.commit()
except SQLAlchemyError as e:
    print(f"Error occurred while checking if the table is empty: {str(e)}")


if __name__ == "__main__":
    rec_bacnet = threading.Thread(target=record_bacnet)
    rec_mbus = threading.Thread(target=record_mbus)
    rec_modbus = threading.Thread(target=record_modbus)
    rec_modbus.start()
    rec_mbus.start()
    rec_bacnet.start()
    uvicorn.run(app, host="0.0.0.0", port=8000)
