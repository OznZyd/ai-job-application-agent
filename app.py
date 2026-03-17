import os
from dotenv import load_dotenv
import google.generativeai as genai
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-pro')


def read_contituion(file_path):
    try:
        with open(file_path, 'r' , encoding='utf-8') as contituion:
            return contituion.read()
    except FileNotFoundError:
        return "Error: Constitution file not found!"
    
presidental_contituon = read_contituion('presidental_contituion.txt')



st.set_page_config(page_title="Job Searching App -with AI", layout="wide")
st.title("AI Job Finder")

st.sidebar.header("Searching Filters")

choice_city = st.sidebar.selectbox("PLease Choice City", ["Amsterdam", "Rotterdam", "Utrecht", "Eindhoven", "Helmond", "Den Haag"])

distance_km = st.sidebar.slider("Maximum Distance to the Center (km)", 0, 100, 25)

min_point = st.sidebar.slider("Minimum Job Score", 0, 100, 25)



my_profile= {
    "Name" : os.getenv("MY_NAME"),
    "Age" : os.getenv("MY_AGE"),
    "Location" : os.getenv("MY_LOCATION"),
    "Engineering Background" : os.getenv("MY_BACKGROUND"),
    "Target and Vision" : os.getenv("MY_TARGET_AND_VISION")
}


engine = create_engine('sqlite:///jobs.db')

df = pd.read_sql("SELECT * FROM job_posting", engine)


filtered_df = df[(df['location'].str.contains(choice_city, case=False, na=False))  & (df['ai_score'].astype(float) >= min_point)]

st.subheader(f"{choice_city} Jobs in the Surrounding Area")

clean_df = filtered_df.drop(columns=['id', 'external_id'], errors='ignore')

def points_colors(value):
    try:
        point = float(value)
    except:
        return ''
    
    if point >= 75:
        return 'background-color: #d9ead3; color: black'
    elif point >= 50:
        return 'background-color: #fff2cc; color: black'
    else:
        return 'background-color: #f4cccc; color: black'

colorful_table = clean_df.style.map(points_colors, subset=['ai_score'])

st.dataframe(colorful_table, hide_index=True)


st.divider()

st.subheader("🗣️ Talk to the Board Chairman (AI Chat)")

chosen_advert = st.selectbox("Which listing do you want to process?", filtered_df['title'])

if chosen_advert:
    st.write(f"**{chosen_advert}** Guide AI is now connected. You can ask your questions.")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    if prompt_text := st.chat_input("Ask the guide: Where to eat, what's the weather like?"):

        with st.chat_message("user"):
            st.markdown(prompt_text)
        st.session_state.messages.append({"role": "user", "content": prompt_text})

        chosen_job_detail = filtered_df[filtered_df['title'] == chosen_advert] ['description'].values[0]
    
        main_instructions = f"""
        {presidental_contituon}

        The job advertisement currently being viewed : {chosen_job_detail}

        User question : {prompt_text}
        """

        ai_response = model.generate_content(main_instructions)
        real_answer = ai_response.text

        with st.chat_message("assistant"):
            st.markdown(real_answer)
        st.session_state.messages.append({"role": "assistant", "content": real_answer})

    
    if st.button(f"{chosen_advert} for prepare a cover letter"):
        st.success(f"{chosen_advert} Your cover letter is ready! Please check the folder.")
        



if not filtered_df.empty:
    st.write("### 🧠 AI Analysis for Best Matches")

    top_job = filtered_df.sort_values(by='ai_score', ascending=False).iloc[0]

    with st.expander(f"Why did AI give {top_job['ai_score']} points to {top_job['title']}?"):
        st.info(top_job['ai_reasoning'])