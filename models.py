from sqlalchemy import Column, Integer, Boolean, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import requests
import os
from dotenv import load_dotenv

load_dotenv()

engine = create_engine('sqlite:///jobs.db')

session = sessionmaker(bind=engine)
db_session = session()


Base = declarative_base()

class JobPosting(Base):

    __tablename__ = 'job_posting'

    id = Column(Integer, primary_key=True)
    external_id = Column(String, unique=True)
    title = Column(String)
    company = Column(String)
    location = Column(String)
    description = Column(String)
    is_applied = Column(Boolean, default=False)

    ai_score = Column(String)
    ai_reasoning = Column(String)


Base.metadata.create_all(engine)


def fetch_jobs(search_query, location):

    url = "https://jsearch.p.rapidapi.com/search"

    headers = {
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": "jsearch.p.rapidapi.com"
    }

    querystring = {"query": search_query,
                    "num_pages": "1",
                    "country": "nl"}

    response = requests.get(url, headers=headers, params=querystring)
    return response.json()


def save_to_db(job_list, session):

    if not job_list:
        print("No listings were received from the API, the list is empty.")
        return

    for i in job_list:
        
        is_it_registered = session.query(JobPosting).filter_by(external_id = i['job_id']).first()

        if is_it_registered is None:

            new_job = JobPosting(
                title=i.get('job_title', 'No Title'),
                company=i.get('employer_name', 'No Company'),
                external_id=i['job_id'],
                description=i.get('job_description', ""),
                location=i.get('job_city', "Netherlands")
            )

            session.add(new_job)
            session.commit()

            print(f"Added new job: {new_job.title}")

        else:
            print(f"Skipping (Already exists): {is_it_registered.title}")



if __name__ == "__main__":

    search_term = "Software Engineer"
    location_term = "Netherlands"

    print(f"Searching for {search_term} in {location_term} ... ")
    api_data = fetch_jobs(search_term, location_term)

    print(f"API stuation: {api_data.get('status')}")

    save_to_db(api_data.get('data', []), db_session)


    print(f"Total number of listings in the database: {db_session.query(JobPosting).count()}")