from datetime import date, datetime, time
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr


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
