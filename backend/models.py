from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship, backref
from datetime import datetime, timezone
from database import Base

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    location_type = Column(String, default="box", nullable=False)
    parent_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    description = Column(Text, nullable=True)
    qr_code = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    children = relationship(
        "Location",
        backref=backref("parent", remote_side=[id])
    )
    items = relationship("Item", back_populates="location")

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    quantity = Column(Integer, default=1)
    is_consumable = Column(Boolean, default=False)
    qr_code = Column(String, unique=True, index=True, nullable=True)
    source_url = Column(String, nullable=True)
    metadata_fields = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    location = relationship("Location", back_populates="items")

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=True)