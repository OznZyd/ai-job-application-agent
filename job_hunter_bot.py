import smtplib
from email.mime.text import MIMEText
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from datetime import datetime
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)


load_dotenv()

base_cv_info = os.getenv("BASE_CV_INFO", "").replace('\\n', '\n')
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

engine = create_engine("sqlite:///jobs.db")
model = genai.GenerativeModel('gemini-2.5-flash')

def send_daily_jobs_email(final_jobs):
    body = "Here are today's top job postings (Golden Tickets included!):\n\n"

    for job in final_jobs:
        body += f" - {job['title']} at {job['company']} (Score: {job['score']}/100)\n"
        body += f" Location: {job['location']}\n"
        body += f" Link: {job['url']}\n\n"

    msg = MIMEText(body)
    msg['Subject'] = '🚀 Daily Top Job Matches'
    msg['From'] = os.getenv("BOT_EMAIL")
    msg['To'] = os.getenv('USER_EMAIL')


    try:
        with smtplib.SMTP_SSL('smtp.gmail.com' , 465) as server:
            server.login(os.getenv('BOT_EMAIL'), os.getenv('BOT_EMAIL_PASSWORD'))
            server.send_message(msg)
            print("Email successfully sent!")
    
    except Exception as e:
        print(f"!!! Email Error: {e}")


def run_job_hunter():

    # 1. Kill Switch Düzeltildi (return eklendi)
    if os.getenv("BOT_ACTIVE") == "False":
        print("Bot is offline. Sleeping...")
        return

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS daily_bot_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                company TEXT,
                description TEXT,
                score INTEGER,
                location TEXT,
                url TEXT,
                date_found TEXT
            )
        """))

        conn.execute(text("DELETE FROM daily_bot_jobs WHERE date_found < date('now', '-30 days')"))

    # 2. Eksik Veriler (URL ve Location) Eklendi
    mock_jobs = [
        {"title": "Junior Backend Developer", "company": "Tech Corp", "description": "Python, SQL, REST APIs.", "url": "http://example.com/1", "location": "Eindhoven"},
        {"title": "Perfect Python Engineer", "company": "DreamTech", "description": "Exactly your CV! Industrial systems, Python, Pandas, eager to learn.", "url": "http://example.com/2", "location": "Helmond"},
        {"title": "Frontend Dev", "company": "Design Studio", "description": "React and CSS required.", "url": "http://example.com/3", "location": "Amsterdam"},
        {"title": "Integration Engineer", "company": "High-Tech BV", "description": "IT/OT bridging and system diagnostics.", "url": "http://example.com/4", "location": "Veldhoven"}
    ]

    for job in mock_jobs:
        ai_prompt = f"""
        Candidate CV: {base_cv_info}
        Job Description: {job['description']}
        Rate how well the candidate matches this job description from 0 to 100.
        Return ONLY the integer number, nothing else.
        """
    
        try:
            ai_response = model.generate_content(ai_prompt).text.strip()
            job['score'] = int(ai_response)
        except Exception as e:
            print(f"!!! AI Error for {job['title']}: {e}")
            job['score'] = 0
            continue

    # 3. GİRİNTİ DÜZELTİLDİ: Bu işlemler döngü (for) bittikten sonra çalışmalı!
    golden_tickets = [job for job in mock_jobs if job['score'] >= 95]
    standart_matches = [job for job in mock_jobs if 80 <= job['score'] < 95]
    top_3_standart = sorted(standart_matches, key=lambda x: x['score'], reverse=True)[:3]

    final_jobs = golden_tickets + top_3_standart

    if not final_jobs:
        print("No suitable job was found today...")
        return
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    with engine.begin() as conn:
        for job in final_jobs:
            conn.execute(
                text("INSERT INTO daily_bot_jobs (title, company, description, score, location, url, date_found) VALUES (:title, :company, :description, :score, :location, :url, :date)"),
                {"title": job['title'], "company": job['company'], "description": job['description'], "score": job['score'], "location": job['location'], "url": job['url'], "date": today_str}
            )

    send_daily_jobs_email(final_jobs)