from fastapi import FastAPI, HTTPException, Depends, Response
from fastapi_sessions.backends.implementations import InMemoryBackend
from fastapi_sessions.session_verifier import SessionVerifier
from fastapi_sessions.frontends.implementations import SessionCookie, CookieParameters
from pydantic import BaseModel
from uuid import UUID, uuid4
from typing import Optional, List
from . import crud, models, schemas
from .database import SessionLocal, engine
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

models.Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=[""],
    allow_headers=[""],
)

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Session management setup
class SessionData(BaseModel):
    user_id: int

cookie_params = CookieParameters()

cookie = SessionCookie(
    cookie_name="session_cookie",
    identifier="session_verifier",
    auto_error=True,
    secret_key="SECRET_KEY",
    cookie_params=cookie_params,
)

backend = InMemoryBackend[UUID, SessionData]()

class BasicVerifier(SessionVerifier[UUID, SessionData]):
    def __init__(
        self,
        *,
        identifier: str,
        auto_error: bool,
        backend: InMemoryBackend[UUID, SessionData],
        auth_http_exception: HTTPException,
    ):
        self._identifier = identifier
        self._auto_error = auto_error
        self._backend = backend
        self._auth_http_exception = auth_http_exception

    @property
    def identifier(self):
        return self._identifier

    @property
    def backend(self):
        return self._backend

    @property
    def auto_error(self):
        return self._auto_error

    @property
    def auth_http_exception(self):
        return self._auth_http_exception

    def verify_session(self, model: SessionData) -> bool:
        """If the session exists, it is valid"""
        return True

verifier = BasicVerifier(
    identifier="session_verifier",
    auto_error=True,
    backend=backend,
    auth_http_exception=HTTPException(status_code=403, detail="Invalid session"),
)

# Create session upon user login
@app.post("/login_session/{user_id}")
async def login_session(user_id: int, response: Response):
    session = uuid4()
    data = SessionData(user_id=user_id)
    await backend.create(session, data)
    cookie.attach_to_response(response, session)
    return {"message": "Session created"}

# Get user ID from session
@app.get("/get_user_id", dependencies=[Depends(cookie)])
async def get_user_id(session_data: SessionData = Depends(verifier)):
    return {"user_id": session_data.user_id}
