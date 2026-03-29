from fastapi import FastAPI
import pandas as pd
from sqlalchemy import create_engine, text
from pydantic import BaseModel
from datetime import datetime



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
    
