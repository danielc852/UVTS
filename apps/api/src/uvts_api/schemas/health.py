from typing import Literal

from pydantic import BaseModel


class LiveResponse(BaseModel):
    status: Literal["live"] = "live"


class ReadyResponse(BaseModel):
    status: Literal["ready"] = "ready"
    database: Literal["ok"] = "ok"
    redis: Literal["ok"] = "ok"
