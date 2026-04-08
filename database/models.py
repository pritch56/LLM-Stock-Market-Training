from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Boolean, JSON, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class RawDocument(Base):
    __tablename__ = "raw_documents"

    id = Column(Integer, primary_key=True)
    url = Column(String(2048), unique=True, nullable=False)
    source_name = Column(String(256))
    raw_html = Column(Text)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    http_status = Column(Integer)
    tags = Column(JSON, default=list)

    processed = relationship("ProcessedDocument", back_populates="raw", uselist=False)


class ProcessedDocument(Base):
    __tablename__ = "processed_documents"

    id = Column(Integer, primary_key=True)
    raw_id = Column(Integer, ForeignKey("raw_documents.id"), unique=True)
    clean_text = Column(Text, nullable=False)
    word_count = Column(Integer)
    language = Column(String(16))
    content_hash = Column(String(64), unique=True)
    processed_at = Column(DateTime, default=datetime.utcnow)

    raw = relationship("RawDocument", back_populates="processed")
    pairs = relationship("InstructionPair", back_populates="source_document")


class InstructionPair(Base):
    __tablename__ = "instruction_pairs"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("processed_documents.id"))
    instruction = Column(Text, nullable=False)
    input = Column(Text, default="")
    output = Column(Text, nullable=False)
    model_used = Column(String(128))
    generation_prompt_tokens = Column(Integer)
    generation_output_tokens = Column(Integer)
    quality_score = Column(Float)
    passed_filters = Column(Boolean, default=True)
    filter_reason = Column(String(512))
    created_at = Column(DateTime, default=datetime.utcnow)
    extra = Column(JSON, default=dict)

    source_document = relationship("ProcessedDocument", back_populates="pairs")
