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
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}
# Target height for scaling before processing (adjust as needed)
# Set to None to skip scaling if videos are expected to be same size
TARGET_HEIGHT = 480
# FFMPEG executable path (if not in system PATH)
FFMPEG_PATH = 'ffmpeg' # Or specify full path like '/usr/local/bin/ffmpeg'

# Set Flask configuration
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
    if not isinstance(files_to_delete, list):
        files_to_delete = [files_to_delete] # Ensure it's a list

    for file_path in files_to_delete:
        if file_path and os.path.exists(file_path): # Check if path is valid and exists
            try:
                os.remove(file_path)
                logging.info(f"Cleaned up temporary file: {file_path}")
            except OSError as e:
                logging.error(f"Error deleting file {file_path}: {e}")
        elif file_path:
             logging.warning(f"Attempted to cleanup non-existent file: {file_path}")


def get_ffmpeg_command(method, input1, input2, output, target_height=None):
    """
    Constructs the FFMPEG command based on the chosen comparison method.

    Args:
        method (str): The comparison method ('side_by_side', 'difference_blend', etc.).
        input1 (str): Path to the first input video.
        input2 (str): Path to the second input video.
        output (str): Path for the output video.
        target_height (int, optional): Target height to scale videos to. Defaults to None.

    Returns:
        list: A list of strings representing the FFMPEG command arguments.
              Returns None if the method is invalid.
    """
    base_command = [
        FFMPEG_PATH,
        '-i', input1,
        '-i', input2,
    ]
    filter_complex = []
    output_map = "[out]" # Default output map

    # --- Scaling (Optional but recommended for consistency) ---
    # Scale inputs before applying comparison filters if target_height is set
    scale_prefix = ""
    input_streams = ["[0:v]", "[1:v]"] # Default input streams for filters
    if target_height:
        # *** FIX: Use w=-2 to ensure width is divisible by 2 for libx264 compatibility ***
        scale_filter = f"scale=w=-2:h={target_height}"
        scale_prefix = f"[0:v]{scale_filter}[v0];[1:v]{scale_filter}[v1];"
        input_streams = ["[v0]", "[v1]"] # Use scaled streams

    # --- Filter Graph Construction based on Method ---
    if method == 'side_by_side':
        filter_complex.append(f"{scale_prefix}{input_streams[0]}{input_streams[1]}hstack=inputs=2{output_map}")
    elif method == 'difference_blend':
        # Blend video 1 onto video 0 using difference mode
        filter_complex.append(f"{scale_prefix}{input_streams[0]}{input_streams[1]}blend=all_mode=difference{output_map}")
    elif method == 'opacity_blend':
        # Using average blend for simplicity (approximates 50% opacity)
        filter_complex.append(f"{scale_prefix}{input_streams[0]}{input_streams[1]}blend=all_mode=average{output_map}")
    elif method == 'interleave':
        # Interleave frames from both inputs
        filter_complex.append(f"{scale_prefix}{input_streams[0]}{input_streams[1]}interleave=n=2{output_map}")
    else:
        logging.error(f"Invalid comparison method requested: {method}")
        return None # Invalid method

    # --- Combine Command Parts ---
    full_command = base_command + [
        '-filter_complex', "".join(filter_complex),
        '-map', output_map,
        '-c:v', 'libx264',       # Video codec (requires even dimensions)
        '-crf', '23',            # Constant Rate Factor
        '-preset', 'veryfast',   # Encoding speed
        '-pix_fmt', 'yuv420p',   # Pixel format compatible with most players/codecs
        '-shortest',             # Finish encoding based on shortest input
        '-y',                    # Overwrite output file
        output
    ]
    return full_command

# --- Routes ---

@app.route('/compare', methods=['POST'])
def compare_videos():
    """
    Handles video uploads, runs FFMPEG for the selected comparison method,
    and returns the path to the output video.
    """
    logging.info("Received request to /compare")
    input1_path, input2_path = None, None # Initialize paths for cleanup
    files_to_cleanup = []

    try:
        # --- 1. Validate Request ---
        if 'video1' not in request.files or 'video2' not in request.files:
            return jsonify({"error": "Missing video file(s) in request"}), 400
        if 'comparison_method' not in request.form:
             return jsonify({"error": "Missing 'comparison_method' in request form"}), 400

        video1 = request.files['video1']
        video2 = request.files['video2']
        method = request.form['comparison_method']

        # Basic filename and type validation
        if video1.filename == '' or video2.filename == '':
            return jsonify({"error": "No selected file or empty filename"}), 400
        if not (allowed_file(video1.filename) and allowed_file(video2.filename)):
            return jsonify({"error": "Invalid file type. Allowed: " + ", ".join(ALLOWED_EXTENSIONS)}), 400

        # --- 2. Save Uploaded Files ---
        unique_id = str(uuid.uuid4())
        ext1 = video1.filename.rsplit('.', 1)[1].lower() if '.' in video1.filename else ''
        ext2 = video2.filename.rsplit('.', 1)[1].lower() if '.' in video2.filename else ''
        input1_filename = f"{unique_id}_1.{ext1}" if ext1 else f"{unique_id}_1"
        input2_filename = f"{unique_id}_2.{ext2}" if ext2 else f"{unique_id}_2"
        # Include method in output filename for clarity
        output_filename = f"{unique_id}_{method}_output.mp4"

        input1_path = os.path.join(app.config['UPLOAD_FOLDER'], input1_filename)
        input2_path = os.path.join(app.config['UPLOAD_FOLDER'], input2_filename)
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        files_to_cleanup.extend([input1_path, input2_path]) # Add inputs for cleanup

        video1.save(input1_path)
        video2.save(input2_path)
        logging.info(f"Saved input videos: {input1_path}, {input2_path}")

        # --- 3. Construct and Run FFMPEG Command ---
        ffmpeg_command = get_ffmpeg_command(method, input1_path, input2_path, output_path, TARGET_HEIGHT)

        if not ffmpeg_command:
            # Invalid method handled in get_ffmpeg_command
            return jsonify({"error": f"Invalid comparison method: {method}"}), 400

        logging.info(f"Running FFMPEG command: {' '.join(ffmpeg_command)}")
        process = subprocess.run(ffmpeg_command, capture_output=True, text=True, check=False)

        # --- 4. Handle FFMPEG Result ---
        if process.returncode != 0:
            error_message = f"FFMPEG failed (method: {method}). Code: {process.returncode}. Error: {process.stderr}"
            logging.error(error_message)
            # Optionally keep output file for debugging FFMPEG errors
            return jsonify({"error": f"Video processing failed. Check server logs. Details: {process.stderr[:500]}..."}), 500
        else:
            logging.info(f"FFMPEG processing successful (method: {method}). Output: {output_path}")
            output_url = f"/outputs/{output_filename}"
            # Return URL and the generated filename for download attribute
            return jsonify({"output_url": output_url, "output_filename": output_filename}), 200

    except Exception as e:
        logging.exception("An unexpected error occurred during /compare request.")
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500

    finally:
        # --- 5. Cleanup ---
        # Ensure cleanup happens even if errors occurred before paths were assigned
        cleanup_files(files_to_cleanup)
        logging.info("Cleanup attempt finished for request.")


@app.route('/outputs/<filename>')
def serve_output_video(filename):
    """Serves the generated video files from the output directory."""
    logging.info(f"Serving output file: {filename}")
    try:
        return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=False)
    except FileNotFoundError:
        logging.error(f"Requested output file not found: {filename}")
        return jsonify({"error": "File not found"}), 404


@app.route('/')
def index():
    """Serves the main HTML page."""
    logging.info("Serving index page.")
    try:
       # Ensure this matches your actual frontend HTML filename
       return send_from_directory('.', 'index.html')
    except FileNotFoundError:
       logging.error("Frontend HTML file 'index.html' not found in the current directory.")
       return "Error: Frontend HTML file not found.", 404


# --- Main Execution ---
if __name__ == '__main__':
    create_directories()
    app.run(host='0.0.0.0', port=5000, debug=True) # Ensure debug is False in production
