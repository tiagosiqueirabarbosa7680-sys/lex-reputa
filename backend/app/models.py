from sqlalchemy import Column, Integer, String
from .database import Base

class Pessoa(Base):
    __tablename__ = "pessoas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    documento = Column(String, unique=True, index=True)  # CPF/CNPJ