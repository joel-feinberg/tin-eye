import os
import subprocess
import uuid
import logging
from flask import Flask, request, jsonify, send_from_directory

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize Flask app
app = Flask(__name__)

# --- Configuration ---
# Directory to store temporary uploaded files
UPLOAD_FOLDER = 'uploads'
# Directory to store generated output videos
OUTPUT_FOLDER = 'outputs'
# Allowed video extensions (adjust as needed)
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}
# Target height for scaling videos before stacking (adjust for quality/performance)
TARGET_HEIGHT = 480

# Set Flask configuration for upload folder (optional, primarily for flask's internal use)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# --- Helper Functions ---

def allowed_file(filename):
    """Checks if the filename has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_directories():
    """Creates upload and output directories if they don't exist."""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    logging.info(f"Ensured directories '{UPLOAD_FOLDER}' and '{OUTPUT_FOLDER}' exist.")

def cleanup_files(files_to_delete):
    """Attempts to delete a list of files, logging any errors."""
    for file_path in files_to_delete:
        try:
            os.remove(file_path)
            logging.info(f"Cleaned up temporary file: {file_path}")
        except OSError as e:
            logging.error(f"Error deleting file {file_path}: {e}")

# --- Routes ---

@app.route('/compare', methods=['POST'])
def compare_videos():
    """
    Handles video uploads, runs FFMPEG for side-by-side comparison,
    and returns the path to the output video.
    """
    logging.info("Received request to /compare")
    files_to_cleanup = []

    try:
        # --- 1. Validate Request ---
        if 'video1' not in request.files or 'video2' not in request.files:
            logging.warning("Request missing 'video1' or 'video2' file part.")
            return jsonify({"error": "Missing video file(s) in request"}), 400

        video1 = request.files['video1']
        video2 = request.files['video2']

        if video1.filename == '' or video2.filename == '':
            logging.warning("One or both submitted files have no filename.")
            return jsonify({"error": "No selected file or empty filename"}), 400

        if not (allowed_file(video1.filename) and allowed_file(video2.filename)):
            logging.warning(f"Invalid file type submitted. Files: {video1.filename}, {video2.filename}")
            return jsonify({"error": "Invalid file type. Allowed types: " + ", ".join(ALLOWED_EXTENSIONS)}), 400

        # --- 2. Save Uploaded Files ---
        # Generate unique filenames to avoid conflicts and potential security issues
        unique_id = str(uuid.uuid4())
        ext1 = video1.filename.rsplit('.', 1)[1].lower()
        ext2 = video2.filename.rsplit('.', 1)[1].lower()
        input1_filename = f"{unique_id}_1.{ext1}"
        input2_filename = f"{unique_id}_2.{ext2}"
        output_filename = f"{unique_id}_output.mp4" # Output as MP4

        input1_path = os.path.join(app.config['UPLOAD_FOLDER'], input1_filename)
        input2_path = os.path.join(app.config['UPLOAD_FOLDER'], input2_filename)
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        # Add input files to cleanup list
        files_to_cleanup.extend([input1_path, input2_path])

        video1.save(input1_path)
        video2.save(input2_path)
        logging.info(f"Saved input videos as: {input1_path}, {input2_path}")

        # --- 3. Construct and Run FFMPEG Command ---
        # Scale both videos to the same TARGET_HEIGHT, then stack horizontally.
        # Use -shortest to make output duration match the shorter input.
        # Use -preset veryfast for faster encoding (adjust crf/preset for quality/speed balance)
        ffmpeg_command = [
            'ffmpeg',
            '-i', input1_path,
            '-i', input2_path,
            '-filter_complex',
            f"[0:v]scale=-1:{TARGET_HEIGHT}[v0];[1:v]scale=-1:{TARGET_HEIGHT}[v1];[v0][v1]hstack=inputs=2[out]",
            '-map', '[out]',         # Map the filtered video stream to output
            '-c:v', 'libx264',       # Video codec
            '-crf', '23',            # Constant Rate Factor (quality, lower is better, 18-28 is sane range)
            '-preset', 'veryfast',   # Encoding speed vs compression (faster speed = larger file)
            '-shortest',             # Finish encoding when the shortest input stream ends
            '-y',                    # Overwrite output file if it exists
            output_path
        ]

        logging.info(f"Running FFMPEG command: {' '.join(ffmpeg_command)}")

        # Execute the command
        process = subprocess.run(ffmpeg_command, capture_output=True, text=True)

        # --- 4. Handle FFMPEG Result ---
        if process.returncode != 0:
            # FFMPEG failed
            error_message = f"FFMPEG failed with code {process.returncode}. Error: {process.stderr}"
            logging.error(error_message)
            # Don't clean up output file if it was partially created and might be useful for debugging
            return jsonify({"error": f"Video processing failed. Check server logs. Details: {process.stderr[:500]}..."}), 500 # Return truncated error
        else:
            # FFMPEG succeeded
            logging.info(f"FFMPEG processing successful. Output: {output_path}")
            # Return the URL path to the generated video
            output_url = f"/outputs/{output_filename}"
            return jsonify({"output_url": output_url}), 200

    except Exception as e:
        # Catch any other unexpected errors during processing
        logging.exception("An unexpected error occurred during /compare request.") # Logs the full traceback
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500

    finally:
        # --- 5. Cleanup ---
        # Always attempt to clean up the uploaded input files
        cleanup_files(files_to_cleanup)
        logging.info("Cleanup attempt finished for request.")


@app.route('/outputs/<filename>')
def serve_output_video(filename):
    """Serves the generated video files from the output directory."""
    logging.info(f"Serving output file: {filename}")
    # Security: Ensure filename doesn't allow directory traversal
    # send_from_directory handles this reasonably well.
    try:
        return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=False) # Serve inline
    except FileNotFoundError:
        logging.error(f"Requested output file not found: {filename}")
        return jsonify({"error": "File not found"}), 404


@app.route('/')
def index():
    """Serves the main HTML page (optional, useful for testing)."""
    # You might serve your index.html directly via Flask or use a dedicated web server like Nginx
    # return "Video Comparison Backend is running. Use the frontend to upload."
    # For simplicity during development, let's serve the frontend HTML directly
    # Make sure 'video_compare_frontend_mvp.html' is in the same directory as this script
    # or adjust the path accordingly. Or better, use Flask's static folder feature.
    # For this example, let's assume the HTML file is named index.html and is in a 'static' subfolder
    # return send_from_directory('static', 'index.html')
    # --- OR --- If you saved the HTML above as 'frontend.html' next to this python script:
    try:
       return send_from_directory('.', 'index.html')
    except FileNotFoundError:
       return "Error: Frontend HTML file not found.", 404


# --- Main Execution ---
if __name__ == '__main__':
    create_directories() # Ensure directories exist before starting
    # Run the Flask app
    # Use host='0.0.0.0' to make it accessible on your network
    # Debug=True is helpful during development but should be OFF in production
    app.run(host='0.0.0.0', port=5000, debug=True)
