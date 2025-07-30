import os
import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# --- LOAD ENVIRONMENT VARIABLES ---
print("Loading environment variables...")
load_dotenv()

# --- INITIALIZE SUPABASE CLIENT ---
print("Initializing Supabase client...")
SUPABASE_URL: str = os.getenv("SUPABASE_URL")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("Supabase client ready.")

# --- INITIALIZE GOOGLE GEMINI CLIENT ---
print("Initializing Google Gemini client...")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-1.5-flash')
print("Gemini client ready.")

# --- LOAD SENTENCE TRANSFORMER MODEL ---
# This is a heavy model, so we only want to load it once.
print("Loading sentence transformer model (this may take a moment)...")
sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
print("Sentence transformer model loaded and ready.")

