from sqlalchemy.orm import Session
import model, schema
from fastapi import HTTPException
from model import BrandResearch, Lead
from schema import BrandResearchCreate
from dotenv import load_dotenv
import os
from jose import jwt
load_dotenv()
from brand_email import get_similar_brands
SECRET = os.environ["secret"]
ALGORITHM = os.environ["algorithm"]


def create_token_password(password: str):
    return jwt.encode({"password": password, "project": "Hustler_AI"},SECRET,algorithm=ALGORITHM)

def create_token_re_password(re_password: str):
    return jwt.encode({"password": re_password, "project": "Hustler_AI"},SECRET,algorithm=ALGORITHM)





# user
def get_user_by_username(db: Session, username: str):
    return db.query(model.UserRegistration).filter(model.UserRegistration.username == username).first()


def get_users(db: Session):
    return db.query(model.UserRegistration).all()


def create_user(db: Session, user: schema.UserCreate):
    db_user = model.UserRegistration(first_name=user.first_name, last_name=user.last_name, username=user.username, email=user.email, phone=user.phone,  password=create_token_password(user.password), re_password=create_token_re_password(user.re_password))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_brand_research(db: Session, brand_research: schema.BrandResearchCreate):
     
   
    
    db_brand_research = BrandResearch(
        brand_name=brand_research.brand_name,
        user_company_info=brand_research.user_company_info,
        outreach_goal=brand_research.outreach_goal,
        desired_cta=brand_research.desired_cta
    )
    db.add(db_brand_research)
    db.commit()
    db.refresh(db_brand_research)

    return db_brand_research

def get_brand_research(db: Session, skip: int = 0, limit: int = 10):
    return db.query(BrandResearch).offset(skip).limit(limit).all()

# def update_brand_research(db: Session, research_id: int, industry: str, similar_brands: list, emails: list, tailored_email: str):
#     # Find the existing research entry
#     brand_research = db.query(BrandResearch).filter(BrandResearch.id == research_id).first()
    
#     if not brand_research:
#         raise Exception("Brand research entry not found")

#     # Update the fields
#     brand_research.industry = industry
    
#     brand_research.similar_brands = similar_brands
#     brand_research.emails = emails
#     brand_research.tailored_email = tailored_email

#     db.commit()  # Commit the changes to the database
#     return brand_research

def get_leads(db: Session):
    return db.query(Lead).all()

def update_lead_status(db: Session, lead_id: int, new_status: str) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if lead:
        lead.status = new_status
        db.commit()
        db.refresh(lead)
        return lead  # This will be converted to a Pydantic model
    return None


def create_email(db: Session, email_address: str, brand_research_id: int, status: str = None):
    email = model.Email(
        email_address=email_address,
        brand_research_id=brand_research_id,
        status=status
    )
    db.add(email)
    db.commit()
    db.refresh(email)
    return email


def create_industry(db: Session, name: str):
    # Check if the industry already exists
    industry = db.query(model.Industry).filter(model.Industry.name == name).first()
    
    if not industry:
        # Create new industry if it doesn't exist
        industry = model.Industry(name=name)
        db.add(industry)
        db.commit()
        db.refresh(industry)
    
    return industry

def create_similar_brand(db: Session, brand_name: str, brand_research_id: int):
    similar_brand = model.SimilarBrand(
        brand_name=brand_name,
        brand_research_id=brand_research_id
    )
    db.add(similar_brand)
    db.commit()
    db.refresh(similar_brand)
    return similar_brand

def create_lead(db: Session, name: str, email: str, company: str, status: str, brand_research_id: int):
    lead = model.Lead(
        name=name,
        email=email,
        company=company,
        status=status,
        brand_research_id=brand_research_id
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


# def save_research_results(db: Session, results: dict, brand_research_id: int, brand_name: str):
#     # Save similar brands
#     for similar_brand in results.get("similar_brands", []):
#         try:
#             create_similar_brand(db, brand_name=similar_brand, brand_research_id=brand_research_id)
#         except Exception as e:
#             print(f"Error saving similar brand '{similar_brand}': {e}")

#     # Save emails
#     for email in results.get("emails", []):
#         try:
#             create_email(db, email_address=email['value'], brand_research_id=brand_research_id, status=email.get('status'))
#         except Exception as e:
#             print(f"Error saving email: {e}")

#     # Fetch or create industry
#     industry_name = results.get(brand_name, {}).get("industry")
#     if industry_name:
#         db_industry = db.query(model.Industry).filter(model.Industry.name == industry_name).first()
#         if not db_industry:
#             db_industry = model.Industry(name=industry_name)
#             db.add(db_industry)
#             db.commit()
#             db.refresh(db_industry)

#         # Associate the brand research entry with the industry
#         brand_research = db.query(model.BrandResearch).filter(model.BrandResearch.id == brand_research_id).first()
#         brand_research.industry = db_industry  # Assign the industry object to the research entry
#     else:
#         print("Industry not found in results")

#     # Save leads
#     for lead in results.get("leads", []):
#         try:
#             create_lead(db, name=lead['name'], email=lead['email'], company=lead['company'], status=lead['status'], brand_research_id=brand_research_id)
#         except Exception as e:
#             print(f"Error saving lead: {e}")

#     db.commit()

def save_research_results(db: Session, results: dict, brand_research_id: int, brand_name: str):
    # Save similar brands
    for similar_brand in results.get("similar_brands", []):
        try:
            create_similar_brand(db, brand_name=similar_brand, brand_research_id=brand_research_id)
        except Exception as e:
            print(f"Error saving similar brand '{similar_brand}': {e}")

    # Check if brand_name exists in results and is a dictionary
    brand_info = results.get(brand_name)
    if isinstance(brand_info, dict):  # Ensure it's a dictionary
        # Get the first email from the results
        email = brand_info.get("emails", [{}])[0].get('value')  # Get the first email value
        if email:
            try:
                create_email(db, email_address=email, brand_research_id=brand_research_id, status='active')
                print(f"Email saved: {email}")
            except Exception as e:
                print(f"Error saving email: {e}")
    else:
        print(f"Error: '{brand_name}' not found in results or is not a dictionary.")

    # Update the name (industry name) in BrandResearch
    industry_name = brand_info.get("name") if brand_info else None  # Ensure brand_info is used correctly
    if industry_name:
        try:
            brand_research = db.query(model.BrandResearch).filter(model.BrandResearch.id == brand_research_id).first()
            if brand_research:
                brand_research.name = industry_name
                db.commit()
                db.refresh(brand_research)
                print(f"Updated industry name: {industry_name}")
            else:
                print(f"Brand research with ID {brand_research_id} not found.")
        except Exception as e:
            print(f"Error updating industry name '{industry_name}': {e}")
    else:
        print("Industry name not found in results")

    # Save leads if present
    for lead in results.get("leads", []):
        try:
            create_lead(db, name=lead['name'], email=lead['email'], company=lead['company'], status=lead['status'], brand_research_id=brand_research_id)
        except Exception as e:
            print(f"Error saving lead '{lead['name']}': {e}")
