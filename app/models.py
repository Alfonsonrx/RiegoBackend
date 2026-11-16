from sqlalchemy import (
    Column, BigInteger, String, Text, Boolean, DateTime,
    Date, Time, Numeric, Integer, ForeignKey, Index, text
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
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    notifications = relationship("Notification", back_populates="user")
    sensors = relationship("Sensor", back_populates="creator")
    schedules = relationship("IrrigationSchedule", back_populates="creator")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("idx_notifications_user_id", "user_id"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(30), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, server_default=text("false"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="notifications")


class Sensor(Base):
    __tablename__ = "sensors"
    __table_args__ = (Index("idx_sensors_created_by", "created_by"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)                  # e.g. "soil_moisture", "temperature"
    unit = Column(String(20), nullable=False)                  # e.g. "%", "°C"
    connection_type = Column(String(20), nullable=False)       # e.g. "wifi", "lora", "ble"
    min_val = Column(Numeric(5, 2), nullable=True)
    max_val = Column(Numeric(5, 2), nullable=True)
    reading_interval_minutes = Column(Integer, nullable=False)
    is_active = Column(Boolean, server_default=text("true"), nullable=False)

    creator = relationship("User", back_populates="sensors")
    readings = relationship("SensorReading", back_populates="sensor")


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (
        Index("idx_sensor_readings_sensor_id", "sensor_id"),
        Index("idx_sensor_readings_recorded_at", "recorded_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sensor_id = Column(BigInteger, ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False)
    value = Column(Numeric(5, 2), nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sensor = relationship("Sensor", back_populates="readings")


class IrrigationSchedule(Base):
    __tablename__ = "irrigation_schedule"
    __table_args__ = (
        Index("idx_irrigation_schedule_created_by", "created_by"),
        Index("idx_irrigation_schedule_date", "irrigation_date"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    irrigation_date = Column(Date, nullable=False)
    irrigation_time = Column(Time, nullable=False)
    is_active = Column(Boolean, server_default=text("true"), nullable=False)

    creator = relationship("User", back_populates="schedules")
