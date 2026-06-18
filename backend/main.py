import os
import re
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

load_dotenv()

from database import init_db, get_session, Lead
from mikrotik import criar_usuario_hotspot

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Hotspot Charle — API de Leads", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class RegistroInput(BaseModel):
    nome: str
    cpf: str
    email: str
    telefone: str
    mac: str | None = None

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) != 11:
            raise ValueError("CPF deve ter 11 dígitos")
        if len(set(digits)) == 1:
            raise ValueError("CPF inválido")
        for i, d in enumerate([9, 10]):
            s = sum(int(digits[j]) * (d + 1 - j) for j in range(d))
            if int(digits[d]) != (s * 10 % 11) % 10:
                raise ValueError("CPF inválido")
        return digits

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Nome deve ter ao menos 3 caracteres")
        return v

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("E-mail inválido")
        return v

    @field_validator("telefone")
    @classmethod
    def validar_telefone(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) < 10:
            raise ValueError("Telefone deve ter ao menos 10 dígitos (com DDD)")
        return digits


@app.post("/api/register")
def registrar(payload: RegistroInput, db: Session = Depends(get_session)):
    try:
        credenciais = criar_usuario_hotspot(payload.cpf, payload.nome, payload.mac)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao criar usuário no MikroTik: {e}")

    # Atualiza lead existente pelo CPF ou cria novo
    lead = db.query(Lead).filter(Lead.cpf == payload.cpf).first()
    if lead:
        lead.nome = payload.nome
        lead.email = payload.email
        lead.telefone = payload.telefone
        lead.mac = payload.mac
        lead.criado_em = datetime.now()
    else:
        lead = Lead(
            nome=payload.nome,
            cpf=payload.cpf,
            email=payload.email,
            telefone=payload.telefone,
            mac=payload.mac,
        )
        db.add(lead)

    db.commit()

    return {
        "ok": True,
        "username": credenciais["username"],
        "password": credenciais["password"],
    }


@app.get("/api/leads")
def listar_leads(db: Session = Depends(get_session)):
    leads = db.query(Lead).order_by(Lead.criado_em.desc()).all()
    return [
        {
            "id": l.id,
            "nome": l.nome,
            "cpf": l.cpf,
            "email": l.email,
            "telefone": l.telefone,
            "mac": l.mac,
            "criado_em": l.criado_em.isoformat() if l.criado_em else None,
        }
        for l in leads
    ]


@app.get("/health")
def health():
    return {"status": "ok"}
