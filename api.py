from fastapi import FastAPI
import pandas as pd
import os
from sqlalchemy import create_engine, text
from pydantic import BaseModel
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv


load_dotenv()

job_search_api = FastAPI()

engine = create_engine('sqlite:///jobs.db')

@job_search_api.get("/api/jobs")
def get_jobs(city: str = "Eindhoven", min_score: int = 70):


    df = pd.read_sql("SELECT * FROM job_posting", engine)

    filtered_df = df[(df['location'].str.contains(city, case=False, na=False)) & (df['ai_score'].astype(float) >= min_score)]

    return filtered_df.to_dict(orient="records")


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

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-pro')

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
    1. Write a strong, attention-grabbing opening.
    2. Highlight the candidate's unique superpower: transitioning from a strong Industrial/OT engineering background into Software Engineering. Emphasize how this diverse perspective brings unique value (e.g., understanding physical consequences of code, system reliability, pragmatic problem-solving) to {data.company_name}.
    3. Connect the candidate's background directly to the requirements in the Job Description.
    4. Keep it concise (max 3-4 paragraphs), modern, and confident. Avoid overly generic clichés.
    5. Output ONLY the cover letter text, ready to be copied and pasted. Do not include any conversational filler.
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