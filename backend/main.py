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
from dotenv import load_dotenv
from brand_email import research_brand, get_industry

load_dotenv()

SECRET = os.environ["secret"]
ALGORITHM = os.environ["algorithm"]


def create_token_password(password: str):
    return jwt.encode(
        {"password": password, "project": "Hustler_AI"},SECRET, algorithm=ALGORITHM)

def create_token_re_password(re_password: str):
    return jwt.encode({"password": re_password, "project": "Hustler_AI"},SECRET,algorithm=ALGORITHM)



def decode_token(token: str):
    return jwt.decode(token, SECRET, algorithms=[ALGORITHM])





oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"login")
model.Base.metadata.create_all(bind=engine)
app = FastAPI()

templates = Jinja2Templates(directory="templates")


client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
HUNTER_API_KEY = os.getenv('HUNTER_API_KEY')



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/signup/", response_class=HTMLResponse)
async def read_signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

#signup
@app.post("/signup/")
def create_user( 
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    re_password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Check if passwords match
    if password != re_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Check if username or email already exists
    db_user = crud.get_user_by_username(db, username=username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # db_email = crud.get_user_by_email(db, email=email)
    # if db_email:
    #     raise HTTPException(status_code=400, detail="Email already registered")
   
    # Create new user
    user_data = schema.UserCreate(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        username=username,
        password=password,
        re_password=re_password
    )
    
    crud.create_user(db=db, user=user_data)
    return RedirectResponse(url="/login/", status_code=302)

   



#login

@app.post("/login/")
def login(
    username: str = Form(...),  # Using Form to accept form data
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    db_user = crud.get_user_by_username(db, username=username)
    if not db_user :
        raise HTTPException(status_code=401, detail="Username is incorrect")
    
    decoded_password = decode_token(db_user.password)  # Decoding the stored password
    if decoded_password["password"] != password:
        raise HTTPException(status_code=401, detail="Password is incorrect")


    # Assuming create_token returns a token to manage user sessions
    
    # Redirect to index.html after successful login
    response = RedirectResponse(url="/index/", status_code=303) 
    
    return response

@app.get("/index/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



@app.get("/login/", response_class=HTMLResponse)
async def read_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})




# user
@app.get("/user/{user_email}", response_model=schema.User)
def read_user(user_email: int, db: Session = Depends(get_db)):
    db_user = crud.get_users(db, user_email=user_email)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.post("/do_research/")
async def do_research(
      brand_name: str = Form(...),
      user_company_info: str = Form(...),
      outreach_goal: str = Form(...),
      desired_cta: str = Form(...),
      db: Session = Depends(get_db),
):
    try:
        # Create a new brand research entry using the Pydantic model
        brand_research_data = BrandResearchCreate(
            brand_name=brand_name,
            user_company_info=user_company_info,
            outreach_goal=outreach_goal,
            desired_cta=desired_cta
        )
        industry=get_industry(brand_research_data.brand_name)
        if industry.endswith('.'):
        # Remove the period and return the result
         industry = industry[:-1]
        # Create a SQLAlchemy model instance
        new_research = model.BrandResearch(
            brand_name=brand_research_data.brand_name,
            user_company_info=brand_research_data.user_company_info,
            outreach_goal=brand_research_data.outreach_goal,
            desired_cta=brand_research_data.desired_cta,name=industry
        )

        # Add the new research entry to the database
        db.add(new_research)
        db.commit()
        db.refresh(new_research)  # Ensure the instance is up to date

        # Now perform the research
        results = research_brand(brand_name, user_company_info, outreach_goal, desired_cta)
        
        # Save the research results
        if isinstance(results, dict) and brand_name in results:
            # Save the research results
            crud.save_research_results(
                db=db,
                results=results,  # Ensure this is correct; it should probably be a model instance or similar.
                brand_research_id=new_research.id,
                brand_name=brand_name
            )
            
            # Update the research entry with results
            crud.update_brand_research(
                db=db,
                research_id=new_research.id,
                industry=results[brand_name].get("industry"),
                similar_brands=results[brand_name].get("similar_brands"),
                emails=results[brand_name].get("emails"),
                tailored_email=results[brand_name].get("tailored_email")
            )
            print("Hello")
        else:
            raise ValueError("Research results are not in the expected format.")
        response_model = BrandResearchResponse.model_validate(new_research)  # Using from_orm to convert model to Pydantic model
        return response_model  # This will return the full model in the response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")



@app.get("/enhanced_results/")
async def get_enhanced_results(brand_name: str, db: Session = Depends(get_db)):
    # Fetch the full research results from the database using the brand_name
    brand_research = db.query(model.BrandResearch).filter(model.BrandResearch.brand_name == brand_name).first()
    
    if not brand_research:
        raise HTTPException(status_code=404, detail="Research not found")

    # Prepare detailed results
    results = {
        "brand_name": brand_research.brand_name,
        "industry": brand_research.industry,
        "similar_brands": brand_research.similar_brands,  # Assuming this is populated
        "emails": brand_research.emails,  # Assuming this is populated
        "tailored_email": brand_research.tailored_email,  # Assuming this is populated
    }
    print(results)
    # Render the enhanced results template
    return templates.TemplateResponse("enhanced_results.html", {"request": Request, "results": results})

@app.get("/results/")
async def get_results(brand_name: str, db: Session = Depends(get_db)):
    # Fetch the research results from the database using the brand_name
    brand_research = db.query(model.BrandResearch).filter(model.BrandResearch.brand_name == brand_name).first()
    
    if not brand_research:
        raise HTTPException(status_code=404, detail="Research not found")

    # Prepare the results to send to the HTML template or response
    results = {
        "brand_name": brand_research.brand_name,
        # Include other fields or related data as needed
    }

    # Return the results as a rendered HTML template or JSON response
    return templates.TemplateResponse("results.html", {"request": Request, "results": results})





@app.get("/crm_dashboard/", response_class=HTMLResponse)
async def crm_dashboard(request: Request, db: Session = Depends(get_db)):
    # if not token:
    #     raise HTTPException(status_code=401, detail="User not authenticated")
    
    leads = crud.get_leads(db)
    return templates.TemplateResponse("crm_dashboard.html", {"request": request, "leads": leads})

@app.post("/update_lead_status", response_model=schema.Lead)  # Use the Pydantic model here
async def update_lead_status(
    lead_id: int = Form(...),
    new_status: str = Form(...),
    db: Session = Depends(get_db)
):
    lead = crud.update_lead_status(db, lead_id=lead_id, new_status=new_status)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

