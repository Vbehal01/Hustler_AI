from fastapi import FastAPI, Form, Depends, HTTPException, Request, Cookie
from sqlalchemy.orm import Session
import model, schema, crud
from database import engine, SessionLocal
from auth import create_token
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from schema import BrandResearchResponse, BrandResearchCreate, UserCreate
from dotenv import load_dotenv
from openai import OpenAI
import os
import requests
import logging
from jose import jwt
import json

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
HUNTER_API_KEY = os.getenv('HUNTER_API_KEY')


def get_similar_brands(brand_name: str):
    """
    Use OpenAI to generate similar brands.
    """
    prompt = f"List 5 companies similar to {brand_name} in the same industry. Provide the response as a comma-separated list."
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that provides information about companies and industries."},
            {"role": "user", "content": prompt}
        ]
    )
    similar_brands = response.choices[0].message.content.strip().split(', ')
    return similar_brands[:5]  # Ensure we only return 5 brands

def get_industry(brand_name: str):
    """
    Use OpenAI to determine the industry of a brand.
    """
    prompt = f"What industry is {brand_name} primarily operating in? Provide a one-word answer."
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that provides information about companies and industries."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# def find_company_emails(domain: str):
#     """
#     Use Hunter.io to find email addresses for a company.
#     """
#     url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}"
#     response = requests.get(url)
#     data = response.json()
#     if 'data' in data and 'emails' in data['data']:
#         return data['data']['emails']
#     return []
def find_company_emails(domain: str):
    """
    Use Hunter.io to find the first email address for a company.
    """
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if 'data' in data and 'emails' in data['data']:
        emails = data['data']['emails']
        if emails:  # Check if emails list is not empty
            first_email = emails[0]['value'] if 'value' in emails[0] else None  # Get first email value
            return first_email  # Return the first email value
    print("No emails found.")  # Print message if no emails are found
    return None  # Return None if no emails are found




def generate_tailored_email(user_company_info: str, recipient_company: str, outreach_goal: str, desired_cta: str):
    """
    Use OpenAI to generate a tailored email.
    """
    prompt = f"""
    Create a professional outreach email with the following details:
    - Sender's company information: {user_company_info}
    - Recipient company: {recipient_company}
    - Outreach goal: {outreach_goal}
    - Desired Call to Action: {desired_cta}
    The email should be concise, friendly, and tailored to the recipient company.
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a professional email writer, crafting personalized outreach emails for business collaborations."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# def research_brand(brand_name: str, user_company_info: str, outreach_goal: str, desired_cta: str):
#     """
#     Combine the brand research logic and return results.
#     """
#     logging.info(f"Starting research for brand: {brand_name}")
#     results = {}
#     try:
#         similar_brands = get_similar_brands(brand_name)
#         logging.info(f"Similar brands found: {similar_brands}")
        
#         # Fetch industry for the brand name
#         industry = get_industry(brand_name)
#         logging.info(f"Industry determined: {industry}")

#         # Store the brand_name related info
#         results[brand_name] = {
#             'similar_brands': similar_brands,
#             'industry': industry
#         }

#         for brand in similar_brands:
#             logging.info(f"Processing similar brand: {brand}")
#             domain = f"www.{brand.lower().replace(' ', '')}.com"
#             emails = find_company_emails(domain)
#             tailored_email = generate_tailored_email(user_company_info, brand, outreach_goal, desired_cta)
#             results[brand] = {
#                 'domain': domain,
#                 'emails': emails,
#                 'tailored_email': tailored_email
#             }

#         logging.info("Research completed successfully")
#         return results
#     except Exception as e:
#         logging.error(f"Error during research: {str(e)}")
#         raise

def research_brand(db_session: Session, brand_name: str, user_company_info: str, outreach_goal: str, desired_cta: str):
    """
    Combine the brand research logic using SQLAlchemy ORM with the 'brand_research' table and return results.
    """
    logging.info(f"Starting research for brand: {brand_name}")
    results = {}

    try:
        # Fetch brand ORM object from the 'brand_research' table using brand_name
        brand = db_session.query(model.BrandResearch).filter_by(brand_name=brand_name).first()

        if not brand:
            logging.error(f"Brand '{brand_name}' not found in database")
            raise ValueError(f"Brand '{brand_name}' not found.")

        # Since there's no industry table, we use the 'name' field for similar brands
        similar_brands = db_session.query(model.BrandResearch).filter_by(name=brand.name).all()
        logging.info(f"Similar brands found: {[b.brand_name for b in similar_brands]}")

        # Store the brand_name related info
        results[brand_name] = {
            'similar_brands': [b.brand_name for b in similar_brands],
            'name': brand.name  # Using the 'name' field directly
        }

        # Loop through each similar brand to gather domain, emails, and tailored email
        for similar_brand in similar_brands:
            logging.info(f"Processing similar brand: {similar_brand.brand_name}")
            domain = f"www.{similar_brand.brand_name.lower().replace(' ', '')}.com"
            emails = find_company_emails(domain)  # Custom function to find emails based on the domain
            tailored_email = generate_tailored_email(user_company_info, similar_brand.brand_name, outreach_goal, desired_cta)
            results[similar_brand.brand_name] = {
                'domain': domain,
                'emails': emails,
                'tailored_email': tailored_email,
                "name": similar_brand.name
            }

        logging.info("Research completed successfully")
        return results

    except Exception as e:
        logging.error(f"Error during research: {str(e)}")
        raise



# def update_brand_research(db: Session, research_id: int, industry: str, similar_brands: list, emails: list, tailored_email: str):
#     research = db.query(model.BrandResearch).filter(model.BrandResearch.id == research_id).first()

#     if research:
#         if industry:
           
#             db_industry = db.query(model.Industry).filter(model.Industry.name == industry).first()
#             if not db_industry:
#                 db_industry = model.Industry(name=industry)
#                 db.add(db_industry)
#                 db.commit()
#                 db.refresh(db_industry)
#             if db_industry:
                
#                 research = db_industry["industry"]
#             print(f"Industry: {type(db_industry)}")
#             print(research)
#         # Clear and add similar brands
#         research.similar_brands.clear()
#         for brand_name in similar_brands:
#             db_similar_brand = model.SimilarBrand(brand_name=brand_name, brand_research_id=research_id)
#             db.add(db_similar_brand)
#             research.similar_brands.append(db_similar_brand)
#             print(f"Similar Brands: {type(db_similar_brand)}")

#         # Clear and add emails
#         research.emails.clear()
#         for email_data in emails:
#             db_email = model.Email(email_address=email_data['value'], status=email_data.get('status'), brand_research_id=research_id)
#             db.add(db_email)
#             research.emails.append(db_email)


#             print(f"Emails: {type(db_email)}")
            

#         # Add tailored email
#         research.tailored_email = tailored_email

#         db.commit()
#         db.refresh(research)

#     return research
def update_brand_research(db: Session, research_id: int, name: str, similar_brands: list, email: str, tailored_email: str):
    research = db.query(model.BrandResearch).filter(model.BrandResearch.id == research_id).first()

    if research:
        # Update the 'name' field directly
        if name:
            research.name = name
            print(f"Updated name: {research.name}")

        # Update similar brands
        research.similar_brands.clear()  # Assuming similar_brands is a relationship or list field in BrandResearch
        for brand_name in similar_brands:
            db_similar_brand = model.SimilarBrand(brand_name=brand_name, brand_research_id=research_id)
            db.add(db_similar_brand)
            research.similar_brands.append(db_similar_brand)
            print(f"Similar Brand: {brand_name}")

        # Update email if it's not None
        if email:
            research.emails.clear()  # Clear previous emails
            db_email = model.Email(email_address=email, status='active', brand_research_id=research_id)  # Create new email
            db.add(db_email)
            research.emails.append(db_email)
            print(f"Email added: {email}")

        # Update tailored email
        research.tailored_email = tailored_email

        # Commit the changes
        db.commit()
        db.refresh(research)

    return research
