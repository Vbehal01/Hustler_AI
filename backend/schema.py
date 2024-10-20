from pydantic import BaseModel
from typing import List, Optional
# user
class UserBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone : str
    username : str

class UserCreate(UserBase):
    password: str
    re_password: str


class User(UserBase):
    id: int

    class Config:
        from_attributes = True

# login_user
class Login(BaseModel):
    username: str
    password: str

    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    token: str

    class Config:
        from_attributes=True



class BrandResearchCreate(BaseModel):
    brand_name: str
    user_company_info: str
    outreach_goal: str
    desired_cta: str
    
    
    class Config:
        from_attributes = True 

class BrandResearchResponse(BrandResearchCreate):
    id: int
    name:str
    #industry: Optional[str] = None
    similar_brands: List[str] 
    emails: List[str] 

    class Config:
         
         from_attributes = True 


class LeadBase(BaseModel):
    id: int
    company_name: str
    email: str
    status: str

class Lead(LeadBase):
    class Config:
        from_attributes = True 