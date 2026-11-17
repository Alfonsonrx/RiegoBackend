from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# One entry per sensor type (102 D1–D3): its unit and the default optimal band (brief: ~80 % RH, 18–24 °C).
SENSOR_TYPES = {
    "humidity": {"unit": "%", "min_val": Decimal("70"), "max_val": Decimal("90")},
    "temperature": {"unit": "°C", "min_val": Decimal("18"), "max_val": Decimal("24")},
}


def _wall_clock(value: time) -> time:
    if value.tzinfo is not None:  # the greenhouse's local time (101 D4), never an offset
        raise ValueError("la hora no lleva zona horaria")
    return value


WallTime = Annotated[time, AfterValidator(_wall_clock)]


class ScheduleCreate(BaseModel):
    irrigation_date: date
    irrigation_time: WallTime


class ScheduleUpdate(BaseModel):
    # Each field may be left out but never sent as null (the columns are NOT NULL); the default None is
    # not validated, so "left out" and "null" stay distinct. model_fields_set says what was sent.
    irrigation_date: date = None
    irrigation_time: WallTime = None
    is_active: bool = None


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    irrigation_date: date
    irrigation_time: time
    is_active: bool


# Sensors (102). Types and connections are closed lists (D1); the unit and the default limits come from the type.
SensorType = Literal[tuple(SENSOR_TYPES)]
Connection = Literal["wifi", "bluetooth"]
SensorName = Annotated[str, Field(min_length=1, max_length=100)]       # sensors.name is String(100)
Interval = Annotated[int, Field(ge=1, le=2**31 - 1)]                    # whole minutes; Integer column
Limit = Annotated[Decimal, Field(max_digits=5, decimal_places=2)]       # Numeric(5, 2): ±999.99


class SensorCreate(BaseModel):
    name: SensorName
    type: SensorType
    connection_type: Connection
    reading_interval_minutes: Interval
    min_val: Limit | None = None  # missing → the type's default (D3)
    max_val: Limit | None = None


class SensorUpdate(BaseModel):
    # Type, unit and connection never change (D6): any field not listed here is rejected.
    # Only the limits may be null (emptied); the others may be left out but not sent as null.
    model_config = ConfigDict(extra="forbid")

    name: SensorName = None
    reading_interval_minutes: Interval = None
    is_active: bool = None
    min_val: Limit | None = None
    max_val: Limit | None = None


class SensorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    unit: str
    connection_type: str
    reading_interval_minutes: int
    min_val: float | None  # a number in JSON, not the string a Decimal would give
    max_val: float | None
    is_active: bool


class SensorCreated(SensorOut):
    ingest_key: str  # shown once; only its hash is stored (D4)


class IngestKeyOut(BaseModel):
    ingest_key: str


class ReadingIn(BaseModel):
    value: Limit  # same Numeric(5, 2) column as the limits: ±999.99 (103 FR-1.e)


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sensor_id: int
    value: float
    recorded_at: datetime


class IngestOut(ReadingOut):
    reading_interval_minutes: int  # tells the device when to send next (103 D2)


class ConditionOut(BaseModel):
    sensor_id: int
    name: str
    type: str
    unit: str
    min_val: float | None
    max_val: float | None
    value: float | None  # None until the sensor sends its first reading (103 FR-3.b)
    recorded_at: datetime | None
