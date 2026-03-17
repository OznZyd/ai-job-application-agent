import os
import json
import time  
import google.generativeai as genai
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import JobPosting, Base

# SETUP
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# DATABASE
engine = create_engine('sqlite:///jobs.db')
Session = sessionmaker(bind=engine)
db_session = Session()


unanalyzed_jobs = db_session.query(JobPosting).filter(JobPosting.ai_score == None).limit(5).all()


model = genai.GenerativeModel('gemini-pro-latest')


for job in unanalyzed_jobs:
    print(f"Evaluating: {job.title} in {job.location}")
    
  
    print("AI is thinking... (waiting 20 seconds for rate limit)")
    time.sleep(20) 
   

    ai_question = f"""
    Evaluate this job for the candidate.
    Candidate Profile: {os.getenv('MY_BACKGROUND')}
    Job Title: {job.title}
    Job Description: {job.description}

    Output ONLY valid JSON format like this:
    {{"score": 85, "reason": "Write a short sentence why it fits."}}
    """

    try:
        response = model.generate_content(ai_question)
        
        
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        ai_result = json.loads(clean_text)

        
        job.ai_score = str(ai_result.get("score"))
        job.ai_reasoning = ai_result.get("reason")
        
        db_session.commit()
        print(f"Success! Score: {job.ai_score} saved.")

    except Exception as e:
       print(f"Error: {e}")
       db_session.rollback()

db_session.close()