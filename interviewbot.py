import streamlit as st
import json
from dotenv import load_dotenv
import openai
import os
import pdfplumber
import docx2txt
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

load_dotenv()
api_key = os.getenv("OPENAI_KEY")
if "llm" not in st.session_state:
    st.session_state.llm = ChatOpenAI(
        model_name="gpt-4",
        temperature=0.5,
        openai_api_key=api_key
    )


def extract_text_from_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return text

def extract_text_from_docx(docx_file):
    return docx2txt.process(docx_file)

def calculate_experience(work_experience):
    """Calculate total years of experience based on extracted work history."""
    total_experience = 0
    for exp in work_experience:
        duration = exp.get("Duration", "0 years")
        years = sum(int(word) for word in duration.split() if word.isdigit())
        total_experience += years
    return total_experience

def extract_resume_data(resume_text):
    extract_prompt = PromptTemplate(
        input_variables=["resume_text"],
        template="""
        Extract the following details from the resume text:
        - Full Name
        - Contact Information (Email, Phone)
        - Job Description(Job Role)
        - Education (Degree, Institute, Year)
        - Work Experience (Company, Role, Duration, Technologies used)
        - Skills (as a comma-separated list)
        - Certifications (if any)
        - Projects (Project Name, Description, Technologies used)

        Resume Text:
        {resume_text}

        - Output the extracted details in JSON format.
        - Strictly only display specified detail and subdetails which are asked in prompt
        - If resume consist of University, Junior College, College, School consider it as Institute during the output
        """
    )
    extract_chain = LLMChain(llm=st.session_state.llm, prompt=extract_prompt)
    extracted_data = extract_chain.run(resume_text)
    try:
        return json.loads(extracted_data)
    except json.JSONDecodeError:
        return None



def generate_interview_questions(resume_data):
    # Calculate work experience
    experience_list = resume_data.get("Work Experience", [])
    total_experience = calculate_experience(experience_list)
    print(total_experience)

    # Handle missing experience
    experience_text = ", ".join([f"{exp['Role']} at {exp['Company']}" for exp in experience_list]) if experience_list else "Not available"
    print(experience_text)
    # Handle missing skills
    skills = resume_data.get("Skills", [])
    skills_text = ", ".join(skills) if skills else "Not available"
    print(skills)
    # Handle missing projects
    projects = resume_data.get("Projects", [])
    projects_text = ", ".join([f"{proj.get('Project Name', 'Unknown')} - {', '.join(proj['Technologies Used']) if isinstance(proj.get('Technologies Used'), list) else str(proj.get('Technologies Used', 'Not specified'))}" for proj in projects]) if projects else "Not available"
    print(projects_text)

    # ==============================
    # Generate Interview Questions
    # ==============================
    if total_experience <= 1:
        experience_category = "0-1 years"
    elif total_experience <= 10:
        experience_category = "2-10 years"
    else:
        experience_category = "10+ years"

    question_prompt = PromptTemplate(
        input_variables=["candidate_name", "skills", "experience", "projects", "experience_level"],
        template="""
        You are a senior technical interviewer preparing **structured interview questions** for a candidate with **{experience_level}** years of experience. 
        The questions must be strictly based on the candidate’s **skills** and **projects**. Adjust complexity based on experience.

        Candidate Name: {candidate_name}  
        Skills: {skills}  
        Experience: {experience}  
        Projects: {projects}  
        Experience Level: {experience_level} years  

        📌 **Question Breakdown**:  

        1️⃣ **Project-based Questions** (2 Questions)  
        - Focus on **technical decision-making**, optimizations, or best practices used in projects.  
        - If **{experience_level} ≤ 1**, ask **basic technology choice** questions.  
        - If **{experience_level} between 2-10**, ask **scalability and performance** questions.  
        - If **{experience_level} ≥ 10**, ask **architecture and high-level strategy** questions.  
        - The **answer must be one word** (e.g., a tool, language, framework, or concept). 
        - What framework did you use for backend development? 

        2️⃣ **Coding Questions** (3 Questions)  
        - Real-world problem-solving, increasing in difficulty:  
            - **Easy** (Basic logic or problem-solving)  
            - **Easy-Moderate** (Data manipulation, algorithms, or sorting)  
            - **Moderate/Hard** (Scalable real-world applications, system efficiency)  
        - **Difficulty Scaling**:  
            - If **{experience_level} ≤ 1**, focus on **data structures, loops, conditions**.  
            - If **{experience_level} between 2-10**, introduce **efficiency, scalability, and practical optimizations**.  
            - If **{experience_level} ≥ 10**, focus on **large-scale system design, performance optimizations, and edge cases**.  
        - **No solution should exceed 100 lines of code**.  
        - **Do not specify any programming language**. 
        - **Question should not be based on specific programming language**.
        - **Given prompt is only for reference do not generate same question**.
        - Given a string, return a new string where each character is repeated the number of times equal to its position in the original string (1-based index). Example:Input: "abc" Output: "abbccc"



        3️⃣ **Technical Fill-in-the-Blanks** (5 Questions)  
        - Must test applied **technical knowledge** from the candidate’s **skills**.  
        - **3 Easy, 2 Moderate-Hard** based on experience level.  
        - If **{experience_level} ≤ 1**, focus on **fundamentals** (definitions, syntax, simple concepts).  
        - If **{experience_level} between 2-10**, include **real-world implementation gaps**.  
        - If **{experience_level} ≥ 10**, test **optimization techniques, advanced architecture**.  
        - The **answer must be one word**.
        - **Given prompt is only for reference do not generate same question**.
        - The primary key in a relational database ensures __________. 
 
        ⚠️ **Guidelines**:  
        - All questions must be **clear, practical, and aligned with the resume**.  
        - Avoid theoretical definitions – prioritize **applied knowledge**.  
        - Ensure diversity in topics (databases, APIs, algorithms, system design, scalability). 
        - No question should display answer after the question.
        - Ensure that the output format should not display Easy, Easy-Moderate, Moderate/Hard after the question

        🎯 **Output Format**:  
        Present the questions in a json format in the following order:  

        **Project-based Questions** - 2
        **Fill-in-the-Blanks** - 5
        **Coding Questions** - 3

        - Generate diverse, unique questions strictly based on the above information.
        
        """
    )

    question_chain = LLMChain(llm=st.session_state.llm, prompt=question_prompt)
    interview_questions = question_chain.run({
        "candidate_name": resume_data.get("Full Name", "Unknown"),
        "job_description": resume_data.get("Job Description", "Not specified"),
        "skills": ", ".join(resume_data.get("Skills", [])) or "No skills listed",
        "experience": ", ".join(
            [f"{exp.get('Role', 'Unknown Role')} at {exp.get('Company', 'Unknown Company')}" 
            for exp in resume_data.get("Work Experience", [])]
        ) or "No work experience listed",
        "projects": ", ".join(
            [f"{proj.get('Project Name', 'Unnamed Project')} - {proj.get('Technologies used', 'Unknown Technologies')}" 
            for proj in resume_data.get("Projects", [])]
        ) or "No projects listed",
        "experience_level": experience_category
        })

    try:
        return json.loads(interview_questions)
    except json.JSONDecodeError:
        return None  



def ui_qa(interview_questions):
    if "user_answer" not in st.session_state:
        st.session_state.user_answer = {}  # Initialize if not exists
    user_answer={}
    for category, q_list in interview_questions.items():
        st.subheader(category)
        
        # Loop through questions
        for i, q in enumerate(q_list, start=1):  # FIX: Proper enumerate usage
            # Extract question text from dictionary if needed
            if isinstance(q, dict):
                q_text = q.get("Question")  # Get value safely
            else:
                q_text = str(q)  # Ensure non-dict questions are strings

            st.write(f"**Q{i}: {q_text}**")

            # Unique key for session state storage
            key = f"answer_{category}_{i}"  # FIX: Unique key with category

            # Store user's answer in session state
            st.session_state.user_answer[q_text] = st.text_area(
                f"Answer for Q{i}",
                value=st.session_state.user_answer.get(q_text, ""),  # Default to previous answer if exists
                key=key  # FIX: Ensures no duplicate keys
            )
    
    return st.session_state.user_answer


def evaluate_answers(questions, answers):
    evaluation_prompt = PromptTemplate(
        input_variables=["questions", "answers"],
        template="""
        You are a senior technical interviewer evaluating a candidate’s responses. Analyze each response based on accuracy, clarity, and depth.

        📌 **Evaluation Breakdown**:  

        1️⃣ **Project-Based Questions** (Technical Decision-Making)  
        - Assess whether the candidate’s answers reflect a solid understanding of their projects.  
        - Evaluate technical choices, optimizations, and best practices.  
       

        2️⃣ **Fill-in-the-Blanks** (Applied Knowledge)  
        - Check factual accuracy and relevance.  
        - Ensure the answers are **one-word** and align with industry standards.  
          

        3️⃣ **Coding Questions** (Problem-Solving & Implementation)  
        - Evaluate correctness, efficiency, and code quality.  
        - Evaluate based logic and do not consider syntax error like indentation,semi colon,brackets.
        - Check if the solution is optimal and handles edge cases.  
        - Strictly check for logic not the format or the langauage used.  

        Candidate’s Responses:  
        {questions}  

        Candidate’s Answers:  
        {answers}  

        🎯 **Evaluation Format**:  
        - **Project Questions**: Score (0-1)  
        - **Fill-in-the-Blanks**: Score (0-1)  
        - **Coding Questions**: Score (0-5)  
        - Present score for each answer.

        📝 **Final Feedback**:  
        - Performance summary across question types.  

        Output the evaluation in a **structured format** without explicitly mentioning these evaluation criteria.
        """
    )


    evaluation_chain = LLMChain(llm=st.session_state.llm, prompt=evaluation_prompt)
    return evaluation_chain.run({"questions": questions, "answers": answers})

# Streamlit UI
def main():
    st.title("Resume Interview Question Generator")

    # File uploader
    uploaded_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

    # Initialize session state variables
    if "resume_text" not in st.session_state:
        st.session_state.resume_text = None

    if "resume_data" not in st.session_state:
        st.session_state.resume_data = None

    if "interview_questions" not in st.session_state:
        st.session_state.interview_questions = None

    if uploaded_file:
        file_type = uploaded_file.type

        # Extract text only once per uploaded file
        if st.session_state.resume_text is None:
            if file_type == "application/pdf":
                st.session_state.resume_text = extract_text_from_pdf(uploaded_file)
            else:
                st.session_state.resume_text = extract_text_from_docx(uploaded_file)

        # Extract structured data only once
        if st.session_state.resume_data is None:
            st.session_state.resume_data = extract_resume_data(st.session_state.resume_text)

        # Display extracted data
        if st.session_state.resume_data:
            st.subheader("Extracted Resume Information")
            st.json(st.session_state.resume_data)

            # Generate Interview Questions Button
            if st.button("Generate Interview Questions"):
                st.session_state.interview_questions = generate_interview_questions(st.session_state.resume_data)

            # Display Questions & Collect User Answers
            if st.session_state.interview_questions:
                st.subheader("Generated Interview Questions")
                user_answers=ui_qa(st.session_state.interview_questions)  # Updates session state with answers

                # Evaluate Answers Button
                if st.button("Evaluate Answers"):
                    evaluation_results = evaluate_answers(st.session_state.interview_questions,user_answers)
                    st.subheader("Evaluation Results")
                    st.write(evaluation_results)

if __name__=="__main__":
    main()                  
