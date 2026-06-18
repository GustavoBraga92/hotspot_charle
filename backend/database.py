from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Session

engine = create_engine("sqlite:///leads.db", echo=False)


class Base(DeclarativeBase):
    pass


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, nullable=False)
    cpf = Column(String(14), nullable=False)
    email = Column(String, nullable=False)
    telefone = Column(String(20), nullable=False)
    mac = Column(String(17), nullable=True)
    criado_em = Column(DateTime, server_default=func.now())


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
