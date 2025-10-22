"""
ORM module using SQLAlchemy.
Usage:
    from orm_models import Session, init_db, File, Word, Display

This file defines the ORM models and helper functions.
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, ForeignKey, LargeBinary, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import os

DB_FILE = os.path.abspath("words.db")
engine = create_engine(f"sqlite:///{DB_FILE}", echo=False, future=True)
Session = sessionmaker(bind=engine, future=True)
Base = declarative_base()


class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, unique=True, nullable=False)

    displays = relationship("Display", back_populates="file", cascade="all, delete-orphan")


class Word(Base):
    __tablename__ = "words"
    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String, nullable=False)
    word_lower = Column(String, nullable=False, index=True)
    trans = Column(String, nullable=False)
    ipa = Column(String)
    gtts = Column(LargeBinary)
    is_unlearned = Column(Boolean, default=True, nullable=False)
    displays = relationship("Display", back_populates="word_ref", cascade="all, delete-orphan")


class Display(Base):
    __tablename__ = "display"
    id = Column(Integer, primary_key=True, autoincrement=True)
    iid = Column(String, unique=True)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)

    word_ref = relationship("Word", back_populates="displays")
    file = relationship("File", back_populates="displays")


def init_db():
    """Create tables if they don't exist."""
    Base.metadata.create_all(engine)


# Convenience helpers
def get_or_create_file(session, filename):
    f = session.query(File).filter_by(filename=filename).first()
    if f:
        return f
    f = File(filename=filename)
    session.add(f)
    session.commit()
    return f


def get_or_create_word(session, word, trans, ipa=None, gtts_bin=None):
    word_lower = word.lower()
    w = session.query(Word).filter_by(word_lower=word_lower, trans=trans).first()
    if w:
        return w
    w = Word(word=word, word_lower=word_lower, trans=trans, ipa=ipa, gtts=gtts_bin)
    session.add(w)
    session.commit()
    return w


