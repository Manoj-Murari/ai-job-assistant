import json
import pandas as pd
from jobspy import scrape_jobs
from config import gemini_model # Import the initialized Gemini client

def run_job_scrape(search_config: dict) -> list:
    """Uses JobSpy to scrape jobs based on a single search configuration."""
    experience_level = search_config.get('experience_level', 'entry_level')
    hours_old = search_config.get('hours_old', 24)

    print(f"\n--- Running search: '{search_config['search_name']}' ---")
    print(f"  - Term: {search_config['search_term']}, Country: {search_config['country']}")
    print(f"  - Experience Level: {experience_level}")
    print(f"  - Max Job Age (Hours): {hours_old}")
    
    try:
        jobs_df: pd.DataFrame = scrape_jobs(
            site_name=["linkedin", "indeed"],
            search_term=search_config['search_term'],
            country=search_config.get('country'),
            experience_level=experience_level,
            hours_old=hours_old,
            job_type='fulltime', 
            results_wanted=30,
            timeout=60
        )
        if jobs_df.empty:
            print(f"  - No new jobs found matching criteria.")
            return []
        
        jobs_list = jobs_df.to_dict('records')
        print(f"  - Found {len(jobs_list)} potential new jobs.")
        return jobs_list
    # --- UPGRADE: More specific error handling ---
    except Exception as e:
        print(f"  - ❗️ An error occurred during scraping for search '{search_config['search_name']}'.")
        print(f"  - ❗️ ERROR DETAILS: {e}")
        # We return an empty list to ensure the application can continue with other searches.
        return []


def get_gemini_analysis(resume_context: str, job_description: str, experience_level: str) -> dict | None:
    """
    Gets a qualitative analysis and rating from the Gemini API with a much stricter prompt
    that now includes experience level filtering.
    """
    print("  > Getting strict qualitative analysis from Gemini...")
    
    # --- FINAL, UPGRADED PROMPT ---
    prompt = f"""
    Act as an extremely strict, expert technical recruiter. Your only goal is to protect my time by filtering out irrelevant job postings.

    MY RESUME CONTEXT:
    ---
    {resume_context}
    ---
    This resume clearly indicates my skills are in SOFTWARE development.

    THE JOB I AM LOOKING FOR:
    ---
    I am looking for an '{experience_level}' role.
    ---

    JOB DESCRIPTION TO ANALYZE:
    ---
    {job_description}
    ---

    YOUR INSTRUCTIONS (Follow these exactly):
    1.  **EXPERIENCE LEVEL CHECK (MOST IMPORTANT):** Analyze the job title and description for keywords related to seniority (e.g., "Senior", "Sr.", "Lead", "Principal", "Manager", "Staff"). If the job requires a higher experience level than '{experience_level}', you MUST give it a low rating and reject it.
    2.  **FIELD RELEVANCE CHECK:** Analyze if the core responsibilities are a strong match for my SOFTWARE skills. Immediately REJECT jobs that are primarily for hardware, mechanical engineering, sales, or other non-software fields.
    3.  **RATING:** Based on BOTH checks above, provide a suitability rating from 1 to 10. A rating of 7 or higher means it is a very strong match for BOTH my software skills AND my desired '{experience_level}'. Be extremely critical.
    4.  **JSON OUTPUT:** Return ONLY a valid JSON object with two keys: "gemini_rating" (int) and "ai_reason" (a concise, one-sentence reason for your rating, explaining why it is or is not a good match for the role and experience level).
    """
    try:
        response = gemini_model.generate_content(prompt)
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"  > Gemini analysis error: {e}")
        return None

def get_resume_suggestions(resume_context: str, job_description: str) -> dict | None:
    # This function remains the same
    """Uses Gemini to generate specific resume tailoring suggestions."""
    print("  > Getting AI resume tailoring suggestions...")
    prompt = f"""
    Act as an expert career coach. Your task is to help me tailor my resume for a specific job.

    My current resume context is:
    ---
    {resume_context}
    ---

    The job description I am applying for is:
    ---
    {job_description}
    ---

    Based on the job description, analyze my resume and provide specific, actionable suggestions for improvement.
    Focus on highlighting relevant skills and experiences.

    Please return ONLY a valid JSON object with one key: "suggestions".
    The value of "suggestions" should be an array of strings, where each string is a specific, well-written bullet point suggestion.
    For example: ["Rephrase 'Managed a team' to 'Led a team of 5 engineers to increase deployment frequency by 30% using Agile methodologies', to better match the leadership skills required.", "Add a bullet point highlighting your experience with 'React' and 'TypeScript' as these are key requirements for the role."]
    """
    try:
        response = gemini_model.generate_content(prompt)
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"  > AI suggestion generation error: {e}")
        return None
