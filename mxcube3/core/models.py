# -*- coding: utf-8 -*-
from typing import Tuple
from pydantic import BaseModel, Field

class HOModel(BaseModel):
    name: str = Field("", description='name of the hardware object')
    state: str = Field("", description='hardware object state')
    msg: str = Field("", description='additional message to display')
    type: str = Field("", description='type of data the object contains')
    available: bool = Field(True, description='True if the object avilable/enabled')
    readonly: bool = Field(True, description='True if the object can only be read (not manipluated)')
    commands: tuple = Field(("set_value", "get_value"), description='List of commands avilable')

    class Config:
        extra: "forbid"

class HOActuatorModel(HOModel):
    value: float = Field(0, description='Value of actuator (position)')
    limits: Tuple[float, float] = Field((-1, -1), description='Limits (min max)')

class NStateModel(HOModel):
    value: str = Field("", description='Value of nstate object')
    limits: Tuple[float, float] = Field((-1, -1), description='Limits (min max)')

class HOMachineInfoModel(HOActuatorModel):
    value: dict = Field(description='Value of machine info')

class HOActuatorValueChangeModel(BaseModel):
    name: str = Field("", description='Name of the hardware object to change')
    value: str = Field("", description='New value of actuator (position)')
