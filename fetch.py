import streamlit as st
import json
import pandas as pd
from dotenv import load_dotenv
import openai
import os
import io
import sqlalchemy
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from sqlalchemy import create_engine, text
#from langchain.sql_database import SQLDatabase
#from langchain.chains import SQLDatabaseChain
#from langchain_experimental.sql import create_sql_query_chain
#from langchain_community.utilities import SQLDatabase
#import dspy_config
#from dspy.integrations import LangChainLM  # Correct import for DSPy integration

# Load environment variables
load_dotenv()

# Database credentials
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Create database engine
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("OPENAI_KEY")

if not st.session_state.api_key:
    st.error("❌ OpenAI API key not found. Check your .env file.")
else:
    llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.5,
            openai_api_key=st.session_state.api_key
        )

# Streamlit Page Config
st.set_page_config(page_title="AI SQL Query Generator", layout="wide")

# Define the database schema as a dictionary
db_schema = {
    "education": {
        "id": "primary key",
        "personal_id": "foreign key referencing personal_details(id)",
        "Degree": "text",
        "Institute": "text",
        "Year": "text"
    },
    "personal_details": {
        "id": "primary key",
        "Full Name": "text",
        "Email": "text",
        "Phone": "BigInt",
        "Job Role": "text",
        "Skills": "text"
    },
    "projects": {
        "id": "primary key",
        "personal_id": "foreign key referencing personal_details(id)",
        "Project Name": "text",
        "Description": "text",
        "Technologies used": "text"
    },
    "work_experience": {
        "id": "primary key",
        "personal_id": "foreign key referencing personal_details(id)",
        "Company": "text",
        "Role": "text",
        "Duration": "text",
        "Technologies used": "text"
    }
}

# Convert schema to a formatted JSON string
formatted_schema = json.dumps(db_schema, indent=4)

# Define the prompt template correctly
sql_prompt = PromptTemplate(
    input_variables=["question", "schema"],  # Explicitly include "schema"
    template="""
    You are an AI SQL expert. Convert the following natural language question into an SQL query.

    Here is the database schema:
    {schema}

    - Ensure that any column names with spaces are enclosed in double quotes.
    - Use standard SQL syntax.
    - All the column name mention in the output should be in "" (Example- "Full Name","Email","Phone","Job Role",etc) and should be in db_schema format.
    - For text make sure to use like operator. 

    Question: {question}
    SQL Query:

    - Only the output query should be displayed.
    """
)


# Streamlit UI
st.title("🔍 AI-Powered SQL Query Generator")
st.subheader("Database Schema")
st.json(db_schema)
user_question = st.text_input("Enter your question:", placeholder="e.g., Show top 5 highest-paid employees")

if st.button("Generate & Run Query"):
    if user_question:
        with st.spinner("Generating SQL query..."):
            try:
                # Generate SQL Query using LLM
                sql_chain = LLMChain(llm=llm, prompt=sql_prompt)
                sql_query = sql_chain.run(question=user_question,schema=formatted_schema)
                st.code(sql_query, language="sql")

                #query = sql_query.content

                # Execute SQL Query
                with engine.connect() as connection:
                    result = connection.execute(text(sql_query))
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())

                st.table(df)


            except Exception as e:
                st.error(f"error: {e}")
    else:
        st.warning("Please enter a question before running.")

