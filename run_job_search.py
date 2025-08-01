import pandas as pd
import math
from sentence_transformers import util
from datetime import datetime

# Import our modularized functions and configurations
from config import sentence_model
from database import get_all_searches, save_job_to_db 
from api_client import run_job_scrape, get_gemini_analysis

# --- HELPER FUNCTIONS (No changes here) ---

def get_similarity_score(resume_embedding, job_description: str) -> float:
    """Calculates the cosine similarity between a resume and job description."""
    if not isinstance(job_description, str) or pd.isna(job_description):
        return 0.0
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

# --- MAIN EXECUTION SCRIPT (UPGRADED LOGIC) ---
def main():
    """The main function to orchestrate the job search and analysis process."""
    print("\n--- Starting Intelli-Apply Pro Job Assistant (Smarter Search Mode) ---")
    
    all_searches = get_all_searches()
    
    if not all_searches:
        print("\nHalting: No saved searches to run.")
        return
    
    # --- THRESHOLDS ---
    SIMILARITY_THRESHOLD = 0.45
    GEMINI_RATING_THRESHOLD = 7
    
    for search in all_searches:
        # --- KEY CHANGE: Get the linked profile and experience level for each search ---
        linked_profile = search.get('profiles')
        experience_level = search.get('experience_level', 'entry_level')
        
        if not linked_profile or not linked_profile.get('resume_context'):
            print(f"\n--- Skipping search: '{search['search_name']}'. No profile is linked. ---")
            continue

        resume_context = linked_profile['resume_context']
        print(f"\n--- Encoding profile '{linked_profile['profile_name']}' for search '{search['search_name']}' ---")
        resume_embedding = sentence_model.encode(resume_context, convert_to_tensor=True)
        
        jobs_found = run_job_scrape(search)
        for job in jobs_found:
            print(f"\nProcessing Job: {job.get('title')}...")
            
            description = job.get("description")
            if not isinstance(description, str) or pd.isna(description):
                print("  > Skipped. Missing job description.")
                continue

            similarity_score = get_similarity_score(resume_embedding, description)

            if similarity_score < SIMILARITY_THRESHOLD:
                print(f"  > Skipped. Similarity score ({similarity_score:.2f}) is below threshold.")
                continue
            
            print(f"  > Passed similarity check: {similarity_score:.2f}.")
            
            # --- KEY CHANGE: Pass the experience level to the AI analyst ---
            gemini_result = get_gemini_analysis(resume_context, description, experience_level)
            
            if not gemini_result or gemini_result.get("gemini_rating", 0) < GEMINI_RATING_THRESHOLD:
                rating = gemini_result.get('gemini_rating', 'N/A') if gemini_result else 'N/A'
                print(f"  > Skipped. Gemini rating ({rating}/10) is below threshold.")
                continue

            print(f"  > SUCCESS! Gemini rated {gemini_result['gemini_rating']}/10. Preparing to save.")
            
            job_to_save = {
                "title": job.get("title"), "company": job.get("company"),
                "job_url": job.get("job_url"), "description": description,
                "similarity_score": similarity_score,
                "gemini_rating": gemini_result.get("gemini_rating"),
                "ai_reason": gemini_result.get("ai_reason"),
                "created_at": datetime.now().isoformat(),
                "profile_id": linked_profile['id'], # Link job to the profile used
                "search_id": search['id'] # Link job to the search used
            }
            
            cleaned_job_to_save = clean_job_data(job_to_save)
            save_job_to_db(cleaned_job_to_save)
            
    print("\n--- Job search process finished. ---")

if __name__ == "__main__":
    main()
