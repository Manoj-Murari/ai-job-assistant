import pandas as pd
import math
from sentence_transformers import util
from datetime import datetime

# Import our new, modularized functions and configurations
from config import sentence_model
from database import get_active_profile, get_all_searches, save_job_to_db
from api_client import run_job_scrape, get_gemini_analysis

# --- HELPER FUNCTIONS (Core processing logic) ---

def get_similarity_score(resume_embedding, job_description: str) -> float:
    """Calculates the cosine similarity between a resume and job description."""
    if not isinstance(job_description, str) or pd.isna(job_description):
        return 0.0
    # Encode the job description using the pre-loaded model
    job_embedding = sentence_model.encode(job_description, convert_to_tensor=True)
    return util.cos_sim(resume_embedding, job_embedding).item()

def clean_job_data(job_dict: dict) -> dict:
    """Replaces any NaN values in a dictionary with None for DB compatibility."""
    cleaned = {}
    for k, v in job_dict.items():
        if isinstance(v, float) and math.isnan(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned

# --- MAIN EXECUTION SCRIPT ---
def main():
    """The main function to orchestrate the job search and analysis process."""
    print("\n--- Starting Intelli-Apply Pro Job Assistant ---")
    
    active_profile = get_active_profile()
    all_searches = get_all_searches()
    
    if not active_profile or not all_searches:
        print("\nHalting: Missing a profile or saved searches to run. Please configure them in the web app.")
        return

    # Prepare resume context and embedding once
    resume_context = active_profile['resume_context']
    print("Encoding active profile for similarity analysis...")
    resume_embedding = sentence_model.encode(resume_context, convert_to_tensor=True)
    print("Profile encoded.")
    
    # --- THRESHOLDS ---
    SIMILARITY_THRESHOLD = 0.45
    GEMINI_RATING_THRESHOLD = 7
    
    for search in all_searches:
        jobs_found = run_job_scrape(search)
        for job in jobs_found:
            print(f"\nProcessing Job: {job.get('title')}...")
            
            description = job.get("description")
            if not isinstance(description, str) or pd.isna(description):
                print("  > Skipped. Missing job description.")
                continue

            # 1. Quantitative Screening (Fast)
            similarity_score = get_similarity_score(resume_embedding, description)

            if similarity_score < SIMILARITY_THRESHOLD:
                print(f"  > Skipped. Similarity score ({similarity_score:.2f}) is below the {SIMILARITY_THRESHOLD} threshold.")
                continue
            
            print(f"  > Passed similarity check: {similarity_score:.2f}.")
            
            # 2. Qualitative Screening (Slower, more expensive)
            gemini_result = get_gemini_analysis(resume_context, description)
            
            if not gemini_result or gemini_result.get("gemini_rating", 0) < GEMINI_RATING_THRESHOLD:
                rating = gemini_result.get('gemini_rating', 'N/A') if gemini_result else 'N/A'
                print(f"  > Skipped. Gemini rating ({rating}/10) is below the {GEMINI_RATING_THRESHOLD} threshold.")
                continue

            # 3. Success! Prepare and save the job
            print(f"  > SUCCESS! Gemini rated {gemini_result['gemini_rating']}/10. Preparing to save.")
            
            job_to_save = {
                "title": job.get("title"),
                "company": job.get("company"),
                "job_url": job.get("job_url"),
                "description": description,
                "similarity_score": similarity_score,
                "gemini_rating": gemini_result.get("gemini_rating"),
                "ai_reason": gemini_result.get("ai_reason"),
                "created_at": datetime.now().isoformat(),
                "profile_id": active_profile['id'],
                "search_id": search['id']
            }
            
            cleaned_job_to_save = clean_job_data(job_to_save)
            save_job_to_db(cleaned_job_to_save)
            
    print("\n--- Job search process finished. ---")

if __name__ == "__main__":
    main()

