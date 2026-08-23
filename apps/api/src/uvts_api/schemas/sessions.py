from pydantic import BaseModel


class SessionBootstrapResponse(BaseModel):
    authenticated: bool = True
    expires_in_seconds: int
