import json
import pandas as pd
from jobspy import scrape_jobs
from config import gemini_model # Import the initialized Gemini client

def run_job_scrape(search_config: dict) -> list:
    """Uses JobSpy to scrape jobs based on a single search configuration."""
    print(f"\n--- Running search: '{search_config['search_name']}' ---")
    print(f"  - Term: {search_config['search_term']}, Country: {search_config['country']}")
    
    try:
        jobs_df: pd.DataFrame = scrape_jobs(
            site_name=["linkedin", "indeed"],
            search_term=search_config['search_term'],
            country=search_config.get('country', 'india'),
            job_type=search_config.get('job_type', 'fulltime'),
            results_wanted=25,
            timeout=45
        )
        if jobs_df.empty:
            print("  - No jobs found for this search.")
            return []
        
        jobs_list = jobs_df.to_dict('records')
        print(f"  - Found {len(jobs_list)} potential jobs.")
        return jobs_list
    except Exception as e:
        print(f"  - An error occurred during scraping: {e}")
        return []


def get_gemini_analysis(resume_context: str, job_description: str) -> dict | None:
    """Gets a qualitative analysis and rating from the Gemini API."""
    print("  > Getting qualitative analysis from Gemini...")
    prompt = f"""
    Based on this resume context: '{resume_context}', analyze the following job description.
    Job Description: '{job_description}'.
    
    Please return ONLY a valid JSON object with two keys:
    1. "gemini_rating": An integer rating from 1 to 10 for how suitable this job is.
    2. "ai_reason": A concise, one-sentence reason for your rating.
    """
    try:
        response = gemini_model.generate_content(prompt)
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"  > Gemini analysis error: {e}")
        return None

# --- NEW: AI RESUME TAILORING FUNCTION ---
def get_resume_suggestions(resume_context: str, job_description: str) -> dict | None:
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

