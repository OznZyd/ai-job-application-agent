import os
import io
import re
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

with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS applied_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            job_title TEXT,
            applied_date TEXT,
            status TEXT DEFAULT 'Ongoing',
            user_notes TEXT,
            ai_cv_data TEXT,
            ai_cover_letter TEXT
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS job_posting (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            title TEXT,
            description TEXT,
            location TEXT,
            ai_score INTEGER,
            ai_reasoning TEXT,
            chat_history TEXT DEFAULT '[]'
        )
    """))

    conn.commit()
    print("Database and 'applied_jobs' table are ready!")

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
gatekeeper_rules = os.getenv("GATEKEEPER_RULES", "").replace('\\n', '\n')
boss_system_prompt = os.getenv("BOSS_SYSTEM_PROMPT", "").replace('\\n', '\n')
cv_optimizer_prompt = os.getenv("CV_OPTIMIZER_PROMPT", "Default CV Prompt")
cover_letter_prompt = os.getenv("COVER_LETTER_PROMPT", "Default Cover Letter Prompt")


genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-pro')


class CvOptimizationRequest(BaseModel):
    project_id: int
    company_name : str
    job_title : str
    job_description : str


@job_search_api.post("/api/optimize-cv")
def optimize_cv(data: CvOptimizationRequest):
    
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT chat_history FROM leads WHERE id = :id"),
            {"id": data.project_id}
        ).fetchone()

        history_str = result[0] if result and result[0] else "[]"
        chat_history = json.loads(history_str)
    
    
    strategy_notes = ""
    for msg in chat_history:
        strategy_notes += f"{msg['sender'].upper()}: {msg['text']}\n"
    
   
    ai_prompt = f"""
    {cv_optimizer_prompt}
    
    Target Company: {data.company_name}
    Target Role: {data.job_title}
    Job Description: {data.job_description}
    
    Base CV:
    {base_cv_info}
    
    Strategy Notes:
    ---
    {strategy_notes}
    ---

    {cv_rules_and_json}
    """

    # 2. Trigger Gemini
    try:
        ai_response = model.generate_content(ai_prompt).text
    except Exception as e:
        print(f"!!! AI Error: {e}")
        return {"status": "error", "message": "Gemini connection failed."}

   
    try:
        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if json_match:
            clean_json = json_match.group(0)
            parsed_data = json.loads(clean_json)
        else:
            raise ValueError("No JSON structure found.")
    except Exception as e:
        print(f"!!! JSON Parsing Error: {e}")
        parsed_data = {
            "SUMMARY": "AI format error. Please try again",
            "SKILLS": [{"category": "Error", "details": "Check logs"}]
        }
       

    try:
        doc = DocxTemplate(TEMPLATE_PATH)

        context = {
            'SUMMARY': parsed_data.get('SUMMARY', 'No summary generated.'),
            'SKILLS': parsed_data.get('SKILLS', []) 
        }

        doc.render(context)

        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0) # Critical: Reset pointer to start

        # Sanitize filename for macOS compatibility
        safe_company = re.sub(r'[^a-zA-Z0-9]', '_', data.company_name)
        
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
    project_id: int
    company_name: str
    job_title: str
    job_description: str

@job_search_api.post("/api/cover-letter")
def generate_cover_letter(data: CoverLetterRequest):
    
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT chat_history FROM leads WHERE id = :id"),
            {"id": data.project_id}
        ).fetchone()

        history_str = result[0] if result and result[0] else "[]"
        chat_history = json.loads(history_str)

    strategy_notes = ""
    for msg in chat_history:
        strategy_notes += f"{msg['sender'].upper()}: {msg['text']}\n"

    ai_prompt = f"""
    {cover_letter_prompt}
    
    Company: {data.company_name}
    Position: {data.job_title}
    Job Description: {data.job_description}
    Candidate Info: {base_cv_info}
    
    Strategy Notes:
    ---
    {strategy_notes}
    ---
    """

    try:
        ai_response = model.generate_content(ai_prompt).text
        ai_body = ai_response.strip()
    except Exception as e:
        print(f"!!! AI Error: {e}")
        return {"status": "error", "message": "Gemini connection failed."}

    try:
        doc = DocxTemplate("cover_letter_template.docx")
        
        context = {
            'DATE': datetime.now().strftime("%B %d, %Y"),
            'COMPANY': data.company_name,
            'AI_BODY': ai_body
        }
        
        doc.render(context)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        safe_company = re.sub(r'[^a-zA-Z0-9]', '_', data.company_name)

        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=Cover_Letter_{safe_company}.docx",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as render_error:
        print(f"!!! WORD/RENDER ERROR: {render_error}")
        return {"status": "error", "message": str(render_error)}



class AiChatRequest(BaseModel):
    job_id: int
    user_message: str
    company: str
    job_description: str

@job_search_api.post("/api/chat")
def chat_with_ai(data: AiChatRequest):
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT chat_history FROM job_posting WHERE id = :id"), {"id": data.job_id}).fetchone()
        history_str = result[0] if result and result[0] else "[]"
        chat_history = json.loads(history_str)

    scout_model = genai.GenerativeModel('gemini-2.5-flash')
    boss_model = genai.GenerativeModel('gemini-2.5-pro')

    gatekeeper_prompt = f"""
    {gatekeeper_rules}
    
    Job Description: {data.job_description}
    User Message: {data.user_message}
    """

    try:
        flash_response = scout_model.generate_content(gatekeeper_prompt).text.strip()
        
        is_boss = False
        ai_response = "" 

        if "[ROUTING_TO_PRESIDENT]" in flash_response:
            print(f"🚨 Gatekeeper triggered for Job {data.job_id}! Waking up the BOSS...")
            is_boss = True
            
            formatted_boss_system = boss_system_prompt.format(company=data.company)
            boss_prompt = f"""
            {formatted_boss_system}
            
            Job Description: {data.job_description}
            Candidate's CV Info: {base_cv_info}
            Candidate's Latest Message: {data.user_message}
            """
            
            ai_response = boss_model.generate_content(boss_prompt).text
        else:
            print(f"⚡ Handled by Scout for Job {data.job_id}.")
            ai_response = flash_response

    
        chat_history.append({"sender": "user", "text": data.user_message})
        chat_history.append({"sender": "ai", "text": ai_response, "isBoss": is_boss})

        with engine.begin() as conn:
            conn.execute(
                text("UPDATE job_posting SET chat_history = :history WHERE id = :id"),
                {"history": json.dumps(chat_history), "id": data.job_id}
            )

        return {"ai_answer": ai_response, "routed_to_pro": is_boss}

    except Exception as e:
        print(f"!!! Global Chat Error: {e}")
        return {"ai_answer": "Connection to the AI Council failed.", "routed_to_pro": False}



@job_search_api.get("/api/applications")
def get_applications():
    try:
        df = pd.read_sql("SELECT * FROM applied_jobs", engine)
        if df.empty:
            return []
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"!!! Database Read Error: {e}")
        return[]
    

class RawJobData(BaseModel):
    raw_text: str

@job_search_api.post("/api/extract-job")
def extract_job(data: RawJobData):

    scout_model = genai.GenerativeModel('gemini-2.5-flash') 

    scout_prompt = f"""
    Act as an Expert IT Recruiter and Data Extractor.
    Analyze the following RAW JOB DESCRIPTION and evaluate it against the CANDIDATE CV.
    
    CANDIDATE CV:
    {base_cv_info}
    
    RAW JOB DESCRIPTION:
    {data.raw_text}
    
    INSTRUCTIONS:
    1. Extract the 'company' name. If not found, use "Unknown Company".
    2. Extract the job 'title'.
    3. Extract the 'location'. If not found, use "Unknown".
    4. Calculate an 'ai_score' (0-100) based on how well the candidate's background matches the job requirements.
    5. Write a 1-sentence 'ai_reasoning' explaining the score. Focus on the transition from OT/Industrial to Software.
    6. Return ONLY a valid JSON object. Do NOT use markdown code blocks like ```json.
    
    EXPECTED JSON FORMAT:
    {{
        "company": "Company Name",
        "title": "Job Title",
        "location": "Location",
        "ai_score": 85,
        "ai_reasoning": "Candidate's strong Python and OT background perfectly matches the system validation requirements."
    }}
    """


    try:
        
        response = scout_model.generate_content(scout_prompt).text

        clean_json = response.replace('```json', '').replace('```', '').strip()
        parsed_data = json.loads(clean_json)

        with engine.connect() as conn:
            query = text("""
                INSERT INTO job_posting
                (company, title, description, location, ai_score, ai_reasoning)
                VALUES (:comp, :title, :desc, :loc, :score, :reasoning)
            """)
            conn.execute(query, {
                "comp": parsed_data.get("company", "Unknown Company"),
                "title": parsed_data.get("title", "Unknown Role"),
                "desc": data.raw_text, # Saving the raw text for the President AI later
                "loc": parsed_data.get("location", "Unknown Location"),
                "score": parsed_data.get("ai_score", 0),
                "reasoning": parsed_data.get("ai_reasoning", "No reasoning provided.")
            })
            conn.commit()
            
        return {"status": "success", "message": "Job extracted and saved successfully!"}
        
    except Exception as e:
        print(f"!!! Scout AI Error: {e}")
        return {"status": "error", "message": str(e)}