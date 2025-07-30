import os
import json
import pandas as pd
from datetime import datetime
import math

# Import powerful libraries for scraping and AI analysis
from jobspy import scrape_jobs
from sentence_transformers import SentenceTransformer, util

# Import Google and Supabase clients
import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv

# --- SETUP ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

print("Loading sentence transformer model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded.")

# --- DYNAMIC DATA FETCHERS ---
def get_active_profile():
    print("Fetching active resume profile...")
    try:
        response = supabase.table('profiles').select('*').order('created_at', desc=True).limit(1).execute()
        if response.data:
            profile = response.data[0]
            print(f"Using profile: '{profile['profile_name']}'")
            return profile
        else:
            print("No profiles found. Please create one in the web app.")
            return None
    except Exception as e:
        print(f"Error fetching profile: {e}")
        return None

def get_all_searches():
    """Fetches all saved search configurations from the database."""
    print("Fetching all saved job searches...")
    try:
        response = supabase.table('searches').select('*').order('created_at', desc=True).execute()
        if response.data:
            print(f"Found {len(response.data)} searches to run.")
            return response.data
        else:
            print("No searches found. Please create a search in the web app.")
            return []
    except Exception as e:
        print(f"Error fetching searches: {e}")
        return []

# --- 1. THE SCRAPER ---
def run_job_scrape(search_config):
    """Uses JobSpy to scrape jobs based on a single search configuration."""
    print(f"\n--- Running search: '{search_config['search_name']}' ---")
    print(f"   - Term: {search_config['search_term']}, Country: {search_config['country']}")
    
    jobs_df: pd.DataFrame = scrape_jobs(
        site_name=["linkedin", "indeed"],
        search_term=search_config['search_term'],
        country=search_config.get('country', 'india'), # Default to India if not specified
        job_type=search_config.get('job_type', 'fulltime'), # Default to fulltime
        results_wanted=25,
        timeout=30
    )
    if jobs_df.empty:
        print("   - No jobs found for this search.")
        return []
    
    jobs_list = jobs_df.to_dict('records')
    print(f"   - Found {len(jobs_list)} potential jobs.")
    return jobs_list

# --- 2. THE AI SCREENER (Functions are the same as before) ---
def get_similarity_score(resume_embedding, job_description):
    if not isinstance(job_description, str) or pd.isna(job_description): return 0.0
    job_embedding = model.encode(job_description, convert_to_tensor=True)
    return util.cos_sim(resume_embedding, job_embedding).item()

def get_gemini_analysis(resume_context, job_description: str):
    print("  > Getting qualitative analysis from Gemini...")
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Based on this resume context: '{resume_context}', rate this job description from 1 to 10 for suitability and give a one-sentence reason. Job Description: '{job_description}'. Return ONLY a valid JSON object with keys 'gemini_rating' (int) and 'ai_reason' (str)."
    try:
        response = gemini_model.generate_content(prompt)
        return json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    except Exception as e:
        print(f"  > Gemini analysis error: {e}")
        return None

# --- 3. THE DATABASE LOADER ---
def save_job_to_db(job_data: dict):
    try:
        job_url = job_data.get('job_url')
        if not job_url:
            print("  > Skipped. Job has no URL.")
            return

        result = supabase.table('jobs').select('id').eq('job_url', job_url).execute()
        if result.data:
            print(f"  > Skipped. Job '{job_data['title']}' already exists.")
            return

        print(f"  > Saving new job '{job_data['title']}' to database...")
        supabase.table('jobs').insert(job_data).execute()
        print("  > Save successful.")
    except Exception as e:
        print(f"  > DB save error: {e}")

# --- DATA CLEANING FUNCTION ---
def clean_job_data(job_dict):
    cleaned = {}
    for k, v in job_dict.items():
        if isinstance(v, float) and math.isnan(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned

# --- MAIN EXECUTION SCRIPT ---
if __name__ == "__main__":
    print("--- Starting Intelli-Apply Pro Job Assistant ---")
    
    active_profile = get_active_profile()
    all_searches = get_all_searches()
    
    if not active_profile or not all_searches:
        print("Halting: Missing a profile or saved searches to run.")
    else:
        resume_context = active_profile['resume_context']
        resume_embedding = model.encode(resume_context, convert_to_tensor=True)
        
        SIMILARITY_THRESHOLD = 0.45
        GEMINI_RATING_THRESHOLD = 7
        
        for search in all_searches:
            jobs_found = run_job_scrape(search)
            for job in jobs_found:
                print(f"Processing Job: {job.get('title')}...")
                
                description = job.get("description")
                if not isinstance(description, str) or pd.isna(description):
                    print("  > Skipped. Missing description.")
                    continue

                similarity_score = get_similarity_score(resume_embedding, description)

                if similarity_score >= SIMILARITY_THRESHOLD:
                    print(f"  > Passed similarity check: {similarity_score:.2f}.")
                    gemini_result = get_gemini_analysis(resume_context, description)
                    
                    if gemini_result and gemini_result.get("gemini_rating", 0) >= GEMINI_RATING_THRESHOLD:
                        print(f"  > SUCCESS! Gemini rated {gemini_result['gemini_rating']}/10.")
                        
                        job_to_save = {
                            "title": job.get("title"), "company": job.get("company"),
                            "job_url": job.get("job_url"), "description": description,
                            "similarity_score": similarity_score,
                            "gemini_rating": gemini_result["gemini_rating"],
                            "ai_reason": gemini_result["ai_reason"],
                            "created_at": datetime.now().isoformat(),
                            "profile_id": active_profile['id'],
                            "search_id": search['id'] # Link job to the search
                        }
                        cleaned_job_to_save = clean_job_data(job_to_save)
                        save_job_to_db(cleaned_job_to_save)
                    else:
                        rating = gemini_result.get('gemini_rating', 'N/A') if gemini_result else 'N/A'
                        print(f"  > Skipped. Gemini rating ({rating}/10) below threshold.")
                else:
                    print(f"  > Skipped. Similarity score ({similarity_score:.2f}) below threshold.")
                print("-" * 20)
            
    print("--- Job search process finished. ---")
