from pydantic import BaseModel


class WorkerCreate(BaseModel):
    employee_number: str | None = None
    name: str
    department: str | None = None
    position: str | None = None


class WorkerUpdate(BaseModel):
    employee_number: str | None = None
    name: str | None = None
    department: str | None = None
    position: str | None = None
    is_active: bool | None = None


class WorkerRead(BaseModel):
    id: str
    employee_number: str | None
    name: str
    department: str | None
    position: str | None
    is_active: bool

    model_config = {"from_attributes": True}

