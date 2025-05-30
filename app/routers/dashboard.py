from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.common_functions.helper_functions import (
    device_data_former,
    widget_data_former,
    history_data_former,
    dashboards_data_former,
)
from app.common_functions.token_handler import JWTBearer
from app.pydantic_models.dashboard import (
    AddWidget,
    WidgetsModel,
    WidgetDelete,
    WidgetHistory,
    AddDashBoard,
    Dashboards as PydanticDashboard,
)
from starlette import status
from app.settings import DB
from app.sql_schemas.models import Devices, Widgets, RawData, DashBoards
from datetime import datetime

router = APIRouter()


@router.post("/dashboard/add_widget", dependencies=[Depends(JWTBearer())])
async def add_widget(
    payload: AddWidget, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = payload.model_dump()
        widget = Widgets(**payload)
        db.add(widget)
        db.commit()
        return {"msg": "Widget Added Successfully"}
    except Exception as err:
        db.rollback()
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/dashboard/devices", dependencies=[Depends(JWTBearer())])
async def dashboard_devices(response: Response = None, db: Session = Depends(DB)):
    try:
        devices = db.query(Devices).filter(~Devices.is_deleted).all()
        devices = list(map(device_data_former, devices))
        return {"data": devices}
    except Exception as err:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/dashboard/widgets", dependencies=[Depends(JWTBearer())])
async def widgets(
    payload: WidgetsModel, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = payload.model_dump()
        widgets = (
            db.query(Widgets)
            .join(Devices)
            .filter(Widgets.dashboard_id == payload["dashboard_id"])
            .all()
        )
        widgets = list(map(widget_data_former, widgets))
        return {"data": widgets}
    except Exception as err:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/dashboard/widgets/delete", dependencies=[Depends(JWTBearer())])
async def delete_widget(
    payload: WidgetDelete, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = payload.model_dump()
        widget = db.query(Widgets).get({"id": payload["id"]})
        if widget:
            db.delete(widget)
            db.commit()
            return {"msg": f"{payload['widget_name']} deleted successfully"}
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": f"{payload['widget_name']} not found. refresh the page"}
    except Exception as err:
        db.rollback()
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/dashboard/widgets/history", dependencies=[Depends(JWTBearer())])
async def widget_history(
    payload: WidgetHistory, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = payload.model_dump()
        raw_data = (
            db.query(RawData)
            .join(Devices)
            .filter(
                Devices.id == payload["device_id"],
                RawData.timestamp >= payload["from_time"],
                RawData.timestamp <= payload["to_time"],
            )
            .order_by(RawData.timestamp.asc())
        ).all()
        data = []
        for item in raw_data:
            data += (
                {
                    **history_data_former(item.tags, item.device.host.type),
                    "timestamp": datetime.fromtimestamp(item.timestamp).strftime(
                        "%d-%m-%Y %H:%M:%S"
                    ),
                },
            )
        return {"data": data}
    except Exception as err:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/dashboard/add_dashboard", dependencies=[Depends(JWTBearer())])
async def add_dashboard(
    payload: AddDashBoard, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = payload.model_dump()
        dashboard = DashBoards(**payload)
        db.add(dashboard)
        db.commit()
        return {"msg": f"{payload['dashboard_name']} added successfully"}
    except Exception as err:
        db.rollback()
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/dashboard/dashboards", dependencies=[Depends(JWTBearer())])
async def dashboards(
    payload: PydanticDashboard, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = payload.model_dump()
        dashboards_raw = (
            db.query(DashBoards).filter(DashBoards.user_id == payload["user_id"]).all()
        )
        dashboards_data = list(map(dashboards_data_former, dashboards_raw))
        return {"msg": "Dashboards fetched successfully", "data": dashboards_data}
    except Exception as err:
        db.rollback()
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}
