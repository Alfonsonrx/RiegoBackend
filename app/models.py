from sqlalchemy import (
    Column, BigInteger, String, Text, Boolean, DateTime,
    Date, Time, Numeric, Integer, ForeignKey
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func
from datetime import datetime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    notifications = relationship("Notification", back_populates="user")
    sensors = relationship("Sensor", back_populates="creator")
    schedules = relationship("IrrigationSchedule", back_populates="creator")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    type = Column(String(30), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)                  # e.g. "soil_moisture", "temperature"
    unit = Column(String(20), nullable=False)                  # e.g. "%", "°C"
    connection_type = Column(String(20), nullable=False)       # e.g. "wifi", "lora", "ble"
    min_val = Column(Numeric(5, 2), nullable=True)
    max_val = Column(Numeric(5, 2), nullable=True)
    reading_interval_minutes = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    creator = relationship("User", back_populates="sensors")
    readings = relationship("SensorReading", back_populates="sensor")


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sensor_id = Column(BigInteger, ForeignKey("sensors.id"), nullable=False)
    value = Column(Numeric(5, 2), nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sensor = relationship("Sensor", back_populates="readings")


class IrrigationSchedule(Base):
    __tablename__ = "irrigation_schedule"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    irrigation_date = Column(Date, nullable=False)
    irrigation_time = Column(Time, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    creator = relationship("User", back_populates="schedules")
