import os
import google.generativeai as genai
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import JobPosting, Base


load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


my_profile= {
    "Name" : os.getenv("MY_NAME"),
    "Age" : os.getenv("MY_AGE"),
    "Location" : os.getenv("MY_LOCATION"),
    "Engineering Background" : os.getenv("MY_BACKGROUND"),
    "Target and Vision" : os.getenv("MY_TARGET_AND_VISION")
}


engine = create_engine('sqlite:///jobs.db')
session = sessionmaker(bind=engine)
db_session = session()

all_jobs = db_session.query(JobPosting).filter(JobPosting.ai_score != None).all()

target_jobs = [job for job in all_jobs if int(job.ai_score) >= 10]


for job in target_jobs:
    print(f"Job creating: {job.company} - {job.description}")

    base_prompt = f"""
    You are a high-level technical recruiter in the Netherlands.
    Using the following candidate profile, craft a bespoke cover letter that 
    highlights how their engineering mindset is an asset for software roles:

    Candidate Data:
    {my_profile}

    TARGET JOB DETAILS:
    Company: {job.company}
    Title: {job.title}
    Description: {job.description}

    TASK: Write a bespoke cover letter that connects the candidate's engineering 
    superpowers specifically to the requirements of this job. 
    Keep it professional, direct (Dutch style), and under 300 words.
    """


    try:
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
        response = model.generate_content(base_prompt)

        safe_company_name = job.company.replace(" ", "_")
        motivation_letter_name = f"job_{safe_company_name}_{job.id}.txt"


        with open(motivation_letter_name, "w", encoding="utf-8") as latter:
            latter.write(response.text)


        print(f"Success! Motivation Letter Created! : {motivation_letter_name}")


    except Exception as error:
        print(f"Error : {error}")

db_session.close()