"""
Declarative Base. Semua model di app/models/ harus inherit dari Base ini,
supaya Alembic autogenerate bisa mendeteksi semua tabel.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
