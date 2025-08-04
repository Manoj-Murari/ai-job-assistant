from flask import Flask, jsonify
from flask_cors import CORS
import threading

# Import the main function from your existing script
from run_job_search import main as run_job_search_script

# --- FLASK APP SETUP ---
app = Flask(__name__)

# --- FIX: Allow requests from multiple frontend ports ---
# This tells the server it's okay to accept requests from your React app
# running on either port 5173 or 5174.
origins = ["http://localhost:5173", "http://localhost:5174"]
CORS(app, resources={r"/run-search": {"origins": origins}})


# A simple variable to prevent multiple searches from running at once
is_search_running = False

def run_script_in_thread():
    """Wrapper function to run the script and handle the lock."""
    global is_search_running
    try:
        print("--- Flask Server: Starting job search script in a new thread. ---")
        run_job_search_script()
    except Exception as e:
        print(f"--- Flask Server: An error occurred in the job search script: {e} ---")
    finally:
        # Once the script is done, allow a new one to start
        is_search_running = False
        print("--- Flask Server: Job search script finished. Ready for new requests. ---")


@app.route('/run-search', methods=['POST'])
def trigger_search():
    """This is the endpoint your frontend will call."""
    global is_search_running
    if is_search_running:
        # If a search is already running, return a conflict error
        return jsonify({"message": "A job search is already in progress."}), 409

    # If no search is running, start a new one
    is_search_running = True
    # We run the script in a separate thread so it doesn't block the server
    thread = threading.Thread(target=run_script_in_thread)
    thread.start()
    
    return jsonify({"message": "Successfully triggered the local job search script."}), 202

if __name__ == '__main__':
    # Run the Flask server on port 5001
    app.run(port=5001, debug=True)
