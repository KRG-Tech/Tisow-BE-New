import time
from sqlalchemy import Column, String, Integer, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    second_name: Mapped[str] = mapped_column(String(50), default="")
    email: Mapped[str] = Column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(15), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    is_admin: Mapped[bool] = mapped_column(default=False)
    timestamp: Mapped[int] = mapped_column(default=lambda: int(time.time()))
    role: Mapped[str] = mapped_column(String(20), default="Engineer")
    rule: Mapped[str] = mapped_column(String(20), default="readonly")

    def as_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "second_name": self.second_name,
            "email": self.email,
            "password": self.password,
            "is_deleted": self.is_deleted,
            "is_admin": self.is_admin,
            "timestamp": self.timestamp,
            "role": self.role,
            "rule": self.rule,
        }


class Devices(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mac: Mapped[str] = mapped_column(String(50), nullable=False)
    device_name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(150), nullable=True)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    instant_id: Mapped[int] = mapped_column(Integer, nullable=True)
    tags: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="inActive")
    other_conf: Mapped[dict] = mapped_column(JSON, nullable=True, default={})
    host_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("device_hosts.id"), nullable=False
    )
    host = relationship(
        "DeviceHosts", back_populates="devices", uselist=False
    )  # uselist=False makes it one-to-one


class DeviceHosts(Base):
    __tablename__ = "device_hosts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    host: Mapped[str] = mapped_column(String(50), nullable=False)
    host_name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    other_conf: Mapped[dict] = mapped_column(JSON, nullable=True, default={})
    devices = relationship("Devices", back_populates="host")


class RawData(Base):
    __tablename__ = "raw_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id"), nullable=False
    )
    device = relationship("Devices")
    timestamp: Mapped[int] = mapped_column(default=lambda: int(time.time()))
    tags: Mapped[dict] = mapped_column(JSON, nullable=True)


class DashBoards(Base):
    __tablename__ = "dashboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dashboard_name: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    user = relationship("Users")


class Widgets(Base):
    __tablename__ = "widgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    widget_name: Mapped[str] = mapped_column(String(50), nullable=False)
    dashboard_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("dashboards.id"), nullable=False
    )
    dashboard = relationship("DashBoards")
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id"), nullable=False
    )
    device = relationship("Devices")
    tags: Mapped[dict] = mapped_column(JSON, nullable=True)
    from_time: Mapped[int] = mapped_column(Integer, nullable=True)
    to_time: Mapped[int] = mapped_column(Integer, nullable=True)
    widget_type: Mapped[str] = mapped_column(String(50), nullable=False)
