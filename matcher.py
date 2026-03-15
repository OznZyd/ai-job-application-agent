import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import JobPosting, Base


load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)



ozan_profile = {
    "yas" : os.getenv("MY_AGE"),
    "konum" : os.getenv("MY_LOCATION"),
    "meslek" : os.getenv("MY_JOB"),
    "hedef" : os.getenv("MY_TARGET")
}


engine = create_engine('sqlite:///jobs.db')
session = sessionmaker(bind=engine)
db_session = session()

unanalyzed_jobs = db_session.query(JobPosting).filter(JobPosting.ai_score == None).limit(5).all()

for jobs in unanalyzed_jobs:
    print(f"evaluated job : {jobs.location}")

    ai_question = f"""
    You are a professional technical recruiter and career transition coach.

    My Candidate Profile:
    {ozan_profile}


    Job Detail:
    Title : {jobs.title}
    Adress : {jobs.location}
    Description : {jobs.description}

    Evaluate this job for me based on my profile. Rate it from 0 to 100.
    Output ONLY valid JSON format like this, do not add markdown or extra text:
    {{"score": 85, "reason": "One sentence explaining why it fits or doesn't fit."}}
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(ai_question)

        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        ai_resulth = json.loads(clean_text)


        jobs.ai_score = str(ai_resulth.get("score"))
        jobs.ai_reasoning = ai_resulth.get("reason")

        db_session.commit()
        print(f"point: {jobs.ai_score} - Saved!")
    
    except Exception as e:
        print(f"An error occurred : {e}")
        db_session.rollback()


db_session.close()








    

