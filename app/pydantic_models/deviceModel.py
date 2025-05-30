from typing import List, Literal, Optional
from pydantic import BaseModel, field_validator, conint
import ipaddress


class BacnetSearch(BaseModel):
    host: str
    host_name: str
    port: conint(ge=1, le=65535)
    host_add: Optional[bool] = True

    @field_validator("host")
    def validate_ip(cls, v):
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError("Invalid IP address")
        return v


class MbusSearch(BaseModel):
    host: str
    device_type: str
    host_name: str
    connection_type: str
    port: conint(ge=1, le=65535)
    com_port: str
    address: conint(ge=1, le=65535)
    baud_rate: conint(ge=1, le=65535)
    host_add: Optional[bool] = True

    @field_validator("host")
    def validate_ip(cls, v):
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError("Invalid IP address")
        return v


class Host(BaseModel):
    host_id: int


class TagModel(BaseModel):
    tag: str
    tag_name: str
    id: int


class DeviceConfig(BaseModel):
    device_name: str
    id: str | int
    mac: str
    description: str
    frequency: int
    manufacturer: str
    tags: List[TagModel]
    other_conf: Optional[dict] = {}


class AddDevice(BaseModel):
    type: str
    host: str
    host_name: str
    port: conint(ge=1)
    device: DeviceConfig
    host_id: Optional[int] = None
    other_conf: Optional[dict] = {}

    @field_validator("host")
    def validate_ip(cls, v):
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError("Invalid IP address")
        return v


class DeleteHostDevice(BaseModel):
    id: int
    device_name: str
    type: Literal["device", "host"]


class GetDevices(BaseModel):
    id: str


class EditHost(BaseModel):
    type: str
    host: str
    host_name: str
    port: conint(ge=1)
    host_id: int
    other_conf: Optional[dict] = {}

    @field_validator("host")
    def validate_ip(cls, v):
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError("Invalid IP address")
        return v


class EditDevice(BaseModel):
    device_name: str
    dev_id: int
    instant_id: Optional[int] = 0
    mac: str
    description: str
    frequency: int
    tags: List[TagModel]
    other_conf: Optional[dict] = {}


class GetTags(BaseModel):
    id: int
    device_name: str
