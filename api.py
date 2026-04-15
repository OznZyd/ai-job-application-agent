import os
import io
import json
from docx import Document
from docxtpl import DocxTemplate
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import pandas as pd
from sqlalchemy import create_engine, text
from pydantic import BaseModel
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "cv_template.docx")


# 1. Initialize FastAPI
job_search_api = FastAPI()

# 2. Add CORS Middleware (Bulletproof setup for local development)
job_search_api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Allow all origins to bypass browser blocks
    allow_credentials=False, # Must be False when allow_origins is ["*"]
    allow_methods=["*"],     # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],     # Allow all headers
)

load_dotenv()

engine = create_engine('sqlite:///jobs.db')

@job_search_api.get("/api/jobs")
async def get_jobs():
    try:
       
        df = pd.read_sql("SELECT * FROM job_posting", engine)
        
        if df.empty:
            return []

        
        df = df.fillna("") 

        
        return df.to_dict(orient="records")
        
    except Exception as e:
        print(f"Backend Hatası: {e}")
        return []


class JobApplication(BaseModel):
    company: str
    job_title: str


@job_search_api.post("/api/jobs")

def save_applications(application_data: JobApplication):

    applied_date = datetime.now().strftime("%Y-%m-%d")

    print(f"Job search request submitted for: {application_data.company}")

    with engine.connect() as conn:


        sql_query = text(f"INSERT INTO applied_jobs (company, job_title, applied_date) VALUES ('{application_data.company}', '{application_data.job_title}', '{applied_date}')")

        conn.execute(sql_query)
        conn.commit()

        return{"message": "The new job has been successfully added to the table." }


interview_secret_strategy = os.getenv("INTERVIEW_SECRET_STRATEGY", "").replace('\\n', '\n')
base_cv_info = os.getenv("BASE_CV_INFO", "").replace('\\n', '\n')
cover_letter_strategy = os.getenv("COVER_LETTER_STRATEGY", "").replace('\\n', '\n')
cv_optimization_strategy = os.getenv("CV_OPTIMIZATION_STRATEGY", "").replace('\\n', '\n')
cv_rules_and_json = os.getenv("CV_RULES_AND_JSON", "").replace('\\n', '\n')


genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-pro')


class CvOptimizationRequest(BaseModel):
    company_name : str
    job_title : str
    job_description : str


@job_search_api.post("/api/optimize-cv")
def optimize_cv(data: CvOptimizationRequest):
    # 1. AI Prompt Construction (Kept exactly as requested)
    ai_prompt = f"""
    Act as an Expert IT/Software Recruiter and Resume Optimizer.
    I will provide you with a base CV and a target Job Description.
    
    Target Company: {data.company_name}
    Target Role: {data.job_title}
    Job Description: {data.job_description}
    
    Base CV:
    {base_cv_info}
    
    {cv_rules_and_json}
    """

    # 2. Trigger Gemini
    try:
        ai_response = model.generate_content(ai_prompt).text
    except Exception as e:
        print(f"!!! AI Error: {e}")
        return {"status": "error", "message": "Gemini connection failed."}

    # 3. Parse JSON response
    try:
        clean_json = ai_response.replace('```json', '').replace('```', '').strip()
        parsed_data = json.loads(clean_json)
    except Exception as e:
        print(f"!!! JSON Parsing Error: {e}")
        parsed_data = {
            "SUMMARY": "AI response format error. Please try again.",
            "SKILLS": [{"category": "Error", "details": "Check logs"}]
        }

    # 4. Word Generation Phase
    try:
        # Load template
        doc = DocxTemplate(TEMPLATE_PATH)

        # Map context safely
        context = {
            'SUMMARY': parsed_data.get('SUMMARY', 'No summary generated.'),
            'SKILLS': parsed_data.get('SKILLS', []) 
        }

        # Render exactly ONCE
        doc.render(context)

        # Save to memory stream
        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0) # Critical: Reset pointer to start

        # Sanitize filename for macOS compatibility
        safe_company = "".join([c if c.isalnum() else "_" for c in data.company_name])
        
        # 5. Return with explicit media type and exposed headers
        return StreamingResponse(
            file_stream, 
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=Optimized_CV_{safe_company}.docx",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as render_error:
        print(f"!!! WORD/RENDER ERROR: {render_error}")
        return {"status": "error", "message": str(render_error)}


class CoverLetterRequest(BaseModel):
    company_name: str
    job_title: str
    job_description: str

@job_search_api.post("/api/cover-letter")
def generate_cover_letter(data: CoverLetterRequest):
    
    ai_prompt = f"""
    Act as an expert Career Coach and Executive Resume Writer.
    Your task is to write a highly compelling, professional, and tailored cover letter for a candidate applying to the {data.job_title} position at {data.company_name}.
    
    Job Description:
    {data.job_description}
    
    Candidate's Background (CV Info):
    {base_cv_info}
    
    INSTRUCTIONS:
    {cover_letter_strategy}
    """

    ai_response = model.generate_content(ai_prompt).text
    return {"cover_letter": ai_response}



class AiChatRequest(BaseModel):
    user_message: str
    company: str
    job_description: str

@job_search_api.post("/api/chat")
def chat_with_ai(data: AiChatRequest):

    ai_prompt = f"""
    Act as an insider Hiring Manager / Senior Tech Lead at {data.company}.
    We are having an informal, pre-interview chat. You have deep knowledge of {data.company}'s corporate culture and engineering standards.
    
    Job Description: {data.job_description}
    Candidate's CV Info: {base_cv_info}
    
    Candidate's Latest Message: {data.user_message}
    
    {interview_secret_strategy}
    
    YOUR INSTRUCTIONS:
    1. Analyze the candidate's last message. Provide direct, senior-level feedback. Tell them what was good, what was missing, and how to say it better in the actual interview.
    2. Share a "Golden Nugget" of insider information about {data.company}.
    3. Ask EXACTLY ONE highly specific, challenging technical or cultural question. Tailor it to the job description AND the candidate's transition from an Industrial/OT background to Software Engineering.
    4. Be pragmatic and realistic, but remember you are ultimately mentoring them to succeed.
    """

    ai_response = model.generate_content(ai_prompt).text

    return {"ai_answer": ai_response}