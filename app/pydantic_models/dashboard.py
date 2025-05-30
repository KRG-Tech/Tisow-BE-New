from typing import List, Optional
from pydantic import BaseModel
from app.pydantic_models.deviceModel import TagModel


class AddDashBoard(BaseModel):
    dashboard_name: str
    user_id: int

class Dashboards(BaseModel):
    user_id: int


class AddWidget(BaseModel):
    widget_name: str
    device_id: int
    tags: List[TagModel]
    from_time: Optional[int] = None
    to_time: Optional[int] = None
    widget_type: str
    dashboard_id: int


class WidgetsModel(BaseModel):
    dashboard_id: int


class WidgetDelete(BaseModel):
    id: int
    widget_name: str


class WidgetHistory(BaseModel):
    device_id: int
    widget_name: str
    from_time: int
    to_time: int
