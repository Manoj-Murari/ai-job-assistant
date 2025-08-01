from config import supabase # Import the initialized Supabase client
from datetime import datetime

def get_all_searches():
    """
    Fetches all saved searches from Supabase and also joins the linked profile data
    so we have the resume context for each search.
    """
    print("Fetching all saved job searches and their linked profiles...")
    try:
        # The key change is here: we are now selecting data from the linked 'profiles' table.
        response = supabase.table('searches').select('*, profiles(id, profile_name, resume_context)').execute()
        
        if response.data:
            print(f"Found {len(response.data)} searches to run.")
            return response.data
        else:
            print("No searches found in database.")
            return []
    except Exception as e:
        print(f"Error fetching searches: {e}")
        return []

# --- No changes to the other functions in this file ---

def get_active_profile():
    """Fetches the most recently created user profile from Supabase."""
    print("Fetching active resume profile from database...")
    try:
        response = supabase.table('profiles').select('*').order('created_at', desc=True).limit(1).execute()
        if response.data:
            profile = response.data[0]
            print(f"Using profile: '{profile['profile_name']}'")
            return profile
        else:
            print("No profiles found in database.")
            return None
    except Exception as e:
        print(f"Error fetching profile: {e}")
        return None

def save_job_to_db(job_data: dict):
    """Saves a single processed job to the Supabase database, avoiding duplicates."""
    try:
        job_url = job_data.get('job_url')
        if not job_url:
            print("  > Skipped save. Job has no URL.")
            return

        # Check if a job with the same URL already exists
        result = supabase.table('jobs').select('id').eq('job_url', job_url).execute()
        if result.data:
            print(f"  > Skipped save. Job '{job_data['title']}' already exists.")
            return

        print(f"  > Saving new job '{job_data['title']}' to database...")
        supabase.table('jobs').insert(job_data).execute()
        print("  > Save successful.")
    except Exception as e:
        print(f"  > DB save error: {e}")
