from contextlib import asynccontextmanager
from datetime import date
import os
import sqlite3
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

DB_PATH = os.getenv("APPLYTRACK_DB_PATH", os.path.join(os.path.dirname(__file__), "applytrack.db"))
Status = Literal["Interested", "Preparing application", "Applied", "Assessment", "Interview", "Offer", "Rejected", "Withdrawn"]


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
