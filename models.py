from sqlalchemy import Column, Integer, Boolean, String
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine


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



engine = create_engine('sqlite:///jobs.db')

Base.metadata.create_all(engine)

