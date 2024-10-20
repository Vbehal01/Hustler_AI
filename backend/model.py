from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.ext.associationproxy import association_proxy
#user

class UserRegistration(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String(15), unique=True, nullable=False)
    username = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    re_password = Column(String, nullable=False)

class BrandResearch(Base):
    __tablename__ = "brand_research"

    id = Column(Integer, primary_key=True, index=True)
    brand_name = Column(String, index=True)
    user_company_info = Column(String)
    outreach_goal = Column(String)
    desired_cta = Column(String)
    name=Column(String)

    
    # industry = relationship("Industry", back_populates="brand_research")

    similar_brands = relationship("SimilarBrand", back_populates="brand_research", cascade="all, delete-orphan")
    emails = relationship("Email", back_populates="brand_research", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="brand_research", cascade="all, delete-orphan")

    # Use association_proxy to simplify access
    similar_brands_names = association_proxy('similar_brands', 'brand_name')
    emails_addresses = association_proxy('emails', 'email_address')
    def __repr__(self):
        return f"<BrandResearch(brand_name={self.brand_name}, outreach_goal={self.outreach_goal})>"

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    company_name = Column(String, index=True)
    email = Column(String, index=True)
    position = Column(String)  # Job title or role
    status = Column(String)  # e.g., contacted, not contacted, etc.

    brand_research_id = Column(Integer, ForeignKey("brand_research.id"))
    brand_research = relationship("BrandResearch", back_populates="leads")

    def __repr__(self):
        return f"<Lead(id={self.id}, company_name={self.company_name}, email={self.email}, status={self.status})>"

class SimilarBrand(Base):
    __tablename__ = "similar_brands"

    id = Column(Integer, primary_key=True, index=True)
    brand_name = Column(String, index=True)

    brand_research_id = Column(Integer, ForeignKey("brand_research.id"))
    brand_research = relationship("BrandResearch", back_populates="similar_brands")

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    email_address = Column(String, index=True)
    status = Column(String)

    brand_research_id = Column(Integer, ForeignKey("brand_research.id"))
    brand_research = relationship("BrandResearch", back_populates="emails")