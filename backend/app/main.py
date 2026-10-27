from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
import json
import os
import re
import sqlite3
from typing import Literal
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4
import secrets

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from fastapi.responses import RedirectResponse

DB_PATH = os.getenv("APPLYTRACK_DB_PATH", os.path.join(os.path.dirname(__file__), "applytrack.db"))
Status = Literal["Interested", "Preparing application", "Applied", "Assessment", "Interview", "Offer", "Rejected", "Withdrawn"]
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_STATES: dict[str, datetime] = {}
GMAIL_CREDENTIALS: dict[str, object] = {}


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def initialize() -> None:
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY, company TEXT NOT NULL, role TEXT NOT NULL, link TEXT,
            location TEXT, status TEXT NOT NULL, applied TEXT, followup TEXT,
            salary TEXT, contact TEXT, notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")


class ApplicationIn(BaseModel):
    company: str = Field(min_length=1, max_length=160)
    role: str = Field(min_length=1, max_length=160)
    link: HttpUrl | None = None
    location: str | None = Field(default=None, max_length=160)
    status: Status = "Interested"
    applied: date | None = None
    followup: date | None = None
    salary: str | None = Field(default=None, max_length=100)
    contact: str | None = Field(default=None, max_length=240)
    notes: str | None = Field(default=None, max_length=5000)


class Application(ApplicationIn):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize()
    yield


app = FastAPI(title="ApplyTrack API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


def _gmail_config() -> tuple[str, str, str]:
    client_id = os.getenv("GMAIL_CLIENT_ID", "")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET", "")
    redirect_uri = os.getenv("GMAIL_REDIRECT_URI", "http://localhost:8000/integrations/gmail/callback")
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="Gmail connection is not configured. Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET on the API server.")
    return client_id, client_secret, redirect_uri


def _gmail_request(url: str, token: str) -> dict:
    request = Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read())
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not read Gmail data. Reconnect Gmail and try again.") from exc


def _refresh_gmail_token() -> str:
    token = GMAIL_CREDENTIALS
    if not token:
        raise HTTPException(status_code=401, detail="Connect Gmail to import sent application emails.")
    expires_at = token.get("expires_at")
    if expires_at and datetime.now(timezone.utc) < expires_at - timedelta(seconds=60):
        return str(token["access_token"])
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Gmail connection expired. Connect Gmail again.")
    client_id, client_secret, _ = _gmail_config()
    body = urlencode({"client_id": client_id, "client_secret": client_secret, "refresh_token": refresh_token, "grant_type": "refresh_token"}).encode()
    request = Request("https://oauth2.googleapis.com/token", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(request, timeout=20) as response:
            renewed = json.loads(response.read())
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not refresh the Gmail connection. Connect Gmail again.") from exc
    token["access_token"] = renewed["access_token"]
    token["expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=int(renewed.get("expires_in", 3600)))
    return str(token["access_token"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/integrations/gmail/status")
def gmail_status() -> dict[str, bool]:
    return {"connected": bool(GMAIL_CREDENTIALS)}


@app.get("/integrations/gmail/connect")
def gmail_connect() -> dict[str, str]:
    client_id, _, redirect_uri = _gmail_config()
    state = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    GMAIL_STATES[state] = now
    for old_state, created in list(GMAIL_STATES.items()):
        if now - created > timedelta(minutes=10):
            del GMAIL_STATES[old_state]
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GMAIL_SCOPE,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state,
    }
    return {"authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)}


@app.get("/integrations/gmail/callback")
def gmail_callback(state: str = "", code: str = "", error: str = "") -> RedirectResponse:
    frontend = os.getenv("FRONTEND_URL", "http://localhost:3000")
    if error:
        return RedirectResponse(f"{frontend}/?gmail=error#applications")
    created = GMAIL_STATES.pop(state, None)
    if not created or datetime.now(timezone.utc) - created > timedelta(minutes=10) or not code:
        raise HTTPException(status_code=400, detail="Gmail authorization expired. Start the connection again.")
    client_id, client_secret, redirect_uri = _gmail_config()
    body = urlencode({"client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri, "grant_type": "authorization_code", "code": code}).encode()
    request = Request("https://oauth2.googleapis.com/token", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(request, timeout=20) as response:
            token = json.loads(response.read())
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Google could not complete the Gmail connection.") from exc
    GMAIL_CREDENTIALS.clear()
    GMAIL_CREDENTIALS.update(token)
    GMAIL_CREDENTIALS["expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=int(token.get("expires_in", 3600)))
    return RedirectResponse(f"{frontend}/?gmail=connected#applications")


@app.get("/integrations/gmail/suggestions")
def gmail_suggestions() -> list[dict[str, str]]:
    token = _refresh_gmail_token()
    query = urlencode({"q": "in:sent newer_than:180d {application job resume cv}", "maxResults": "20"})
    listed = _gmail_request(f"https://gmail.googleapis.com/gmail/v1/users/me/messages?{query}", token)
    suggestions: list[dict[str, str]] = []
    for message in listed.get("messages", []):
        detail = _gmail_request(f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message['id']}?format=metadata&metadataHeaders=Subject&metadataHeaders=Date", token)
        headers = {h["name"].lower(): h["value"] for h in detail.get("payload", {}).get("headers", [])}
        subject = headers.get("subject", "Application email")
        match = re.search(r"(?:application(?:\s+for)?|applying for)\s+(.+?)\s+(?:at|to)\s+(.+)", subject, re.IGNORECASE)
        suggestions.append({
            "id": str(message["id"]),
            "subject": subject,
            "role": match.group(1).strip(" -–—") if match else subject,
            "company": match.group(2).strip(" -–—") if match else "",
            "date": headers.get("date", ""),
        })
    return suggestions


@app.delete("/integrations/gmail", status_code=204)
def gmail_disconnect() -> Response:
    GMAIL_CREDENTIALS.clear()
    return Response(status_code=204)


@app.get("/applications", response_model=list[Application])
def list_applications() -> list[dict]:
    with connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM applications ORDER BY applied DESC, created_at DESC")]


@app.post("/applications", response_model=Application, status_code=201)
def create_application(payload: ApplicationIn) -> dict:
    record = payload.model_dump(mode="json")
    record["id"] = str(uuid4())
    columns = ["id", *payload.model_fields]
    with connect() as db:
        db.execute(f"INSERT INTO applications ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", [record.get(column) for column in columns])
        row = db.execute("SELECT * FROM applications WHERE id = ?", (record["id"],)).fetchone()
    return dict(row)


@app.put("/applications/{application_id}", response_model=Application)
def update_application(application_id: str, payload: ApplicationIn) -> dict:
    record = payload.model_dump(mode="json")
    columns = list(payload.model_fields)
    with connect() as db:
        cursor = db.execute(f"UPDATE applications SET {','.join(f'{column} = ?' for column in columns)} WHERE id = ?", [record[column] for column in columns] + [application_id])
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Application not found")
        row = db.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
    return dict(row)


@app.delete("/applications/{application_id}", status_code=204)
def delete_application(application_id: str) -> Response:
    with connect() as db:
        cursor = db.execute("DELETE FROM applications WHERE id = ?", (application_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Application not found")
    return Response(status_code=204)
