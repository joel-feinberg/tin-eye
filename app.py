import os
import subprocess
import uuid
import logging
from flask import Flask, request, jsonify, send_from_directory
import math # For ceiling function

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize Flask app
app = Flask(__name__)

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
# *** Added 'webm' to allowed extensions ***
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
TARGET_HEIGHT = 480 # Target height for scaling (keeps aspect ratio)
FFMPEG_PATH = 'ffmpeg' # Path to ffmpeg executable
QUICK_TEST_FILE_1 = os.path.join(UPLOAD_FOLDER, 'old.mp4')
QUICK_TEST_FILE_2 = os.path.join(UPLOAD_FOLDER, 'new.mp4')
# Methods that benefit from pre-comparison tinting
TINTING_METHODS = {'difference_blend', 'subtract_blend', 'opacity_blend'}
# Methods that benefit from post-comparison brightness boost
BRIGHTNESS_BOOST_METHODS = {'difference_blend', 'subtract_blend'}

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
        files_to_delete = [files_to_delete]
    for file_path in files_to_delete:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logging.info(f"Cleaned up temporary file: {file_path}")
            except OSError as e:
                logging.error(f"Error deleting file {file_path}: {e}")
        elif file_path:
             logging.warning(f"Attempted to cleanup non-existent file: {file_path}")


def get_ffmpeg_command(method, input1, input2, output, target_height=None, playback_speed=1.0):
    """
    Constructs the FFMPEG command with scaling, tinting, comparison, brightness boost,
    and video speed adjustment. Audio processing is removed.
    Uses component expressions blend for color_channel_mix.
    Uses overlay for interleave/blinking.
    """
    try:
        playback_speed = float(playback_speed)
        if playback_speed <= 0:
            logging.warning("Playback speed must be positive, defaulting to 1.0")
            playback_speed = 1.0
    except (ValueError, TypeError):
        logging.warning("Invalid playback speed value, defaulting to 1.0")
        playback_speed = 1.0

    base_command = [ FFMPEG_PATH, '-i', input1, '-i', input2 ]
    filter_complex_parts = []
    video_inputs = ["[0:v]", "[1:v]"] # Initial video stream identifiers

    # --- 1. Scaling (if target_height is set) ---
    if target_height:
        scale_filter = f"scale=w=-2:h={target_height}"
        filter_complex_parts.append(f"{video_inputs[0]}{scale_filter}[scaled0]")
        filter_complex_parts.append(f"{video_inputs[1]}{scale_filter}[scaled1]")
        video_inputs = ["[scaled0]", "[scaled1]"]

    # --- 2. Tinting (Optional, before certain blend modes) ---
    tinted_video_inputs = list(video_inputs) # Copy the list
    if method in TINTING_METHODS:
        filter_complex_parts.append(f"{video_inputs[0]}colorbalance=bs=0.1[tinted0]")
        filter_complex_parts.append(f"{video_inputs[1]}colorbalance=gs=0.1[tinted1]")
        tinted_video_inputs = ["[tinted0]", "[tinted1]"]

    # --- 3. Main Comparison Filter ---
    comparison_output_tag = "[comp_out]"
    post_comparison_tag = comparison_output_tag # Tag after comparison, before brightness boost

    if method == 'side_by_side':
        filter_complex_parts.append(f"{video_inputs[0]}{video_inputs[1]}hstack=inputs=2{comparison_output_tag}")
    elif method == 'vertical_stack':
        filter_complex_parts.append(f"{video_inputs[0]}{video_inputs[1]}vstack=inputs=2{comparison_output_tag}")
    elif method == 'difference_blend':
        filter_complex_parts.append(f"{tinted_video_inputs[0]}{tinted_video_inputs[1]}blend=all_mode=difference{comparison_output_tag}")
    elif method == 'subtract_blend':
        filter_complex_parts.append(f"{tinted_video_inputs[0]}{tinted_video_inputs[1]}blend=all_mode=subtract{comparison_output_tag}")
    elif method == 'opacity_blend':
        filter_complex_parts.append(f"{tinted_video_inputs[0]}{tinted_video_inputs[1]}blend=all_mode=average{comparison_output_tag}")
    elif method == 'interleave':
        # *** FIX: Use overlay with enable='mod(n,2)' for blinking effect ***
        # Shows input 0 on even frames (n=0, 2, 4...), overlays input 1 on odd frames (n=1, 3, 5...)
        filter_complex_parts.append(f"{video_inputs[0]}{video_inputs[1]}overlay=enable='mod(n,2)'{comparison_output_tag}")
    elif method == 'color_channel_mix':
        # Use component expressions
        blend_options = "c0_expr='A':c1_expr='(A+B)/2':c2_expr='B'"
        filter_complex_parts.append(f"{video_inputs[0]}{video_inputs[1]}blend={blend_options}{comparison_output_tag}")
    else:
        logging.error(f"Invalid comparison method requested: {method}")
        return None

    # --- 3.5 Brightness Boost (Optional, after difference/subtract) ---
    boosted_output_tag = post_comparison_tag # Start with the output from comparison
    if method in BRIGHTNESS_BOOST_METHODS:
        boost_filter = "lutyuv=y=val*4" # Multiply luma by 4 (adjust multiplier as needed)
        boosted_output_tag = "[boosted]"
        filter_complex_parts.append(f"{post_comparison_tag}{boost_filter}{boosted_output_tag}")


    # --- 4. Speed Adjustment (Video Only) ---
    final_video_tag = boosted_output_tag # Use the potentially boosted output tag

    if not math.isclose(playback_speed, 1.0):
        speed_factor = 1.0 / playback_speed
        # Apply setpts to the video stream coming from the comparison/boost stage
        filter_complex_parts.append(f"{boosted_output_tag}setpts={speed_factor}*PTS[final_v]")
        final_video_tag = "[final_v]" # Update the tag for the final video stream

    # --- 5. Combine Command ---
    filter_complex_string = ";".join(filter_complex_parts)
    full_command = base_command + ['-filter_complex', filter_complex_string]

    # Map only the final video stream
    full_command.extend(['-map', final_video_tag])

    # Output options
    full_command.extend([
        '-c:v', 'libx264',
        '-crf', '23',
        '-preset', 'veryfast',
        '-pix_fmt', 'yuv420p',
        '-an', # Explicitly disable audio recording
        '-shortest',
        '-y',
        output
    ])
    return full_command

# --- Route Handlers ---

def process_request(method, input1_path, input2_path, playback_speed, is_local=False):
    """Shared logic for processing video comparison."""
    unique_id = str(uuid.uuid4())
    output_prefix = "local" if is_local else "upload"
    speed_str = str(playback_speed).replace('.', 'p') # Format speed for filename
    output_filename = f"{unique_id}_{method}_{output_prefix}_s{speed_str}x_output.mp4"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

    # Construct and Run FFMPEG Command
    ffmpeg_command = get_ffmpeg_command(method, input1_path, input2_path, output_path, TARGET_HEIGHT, playback_speed)

    if not ffmpeg_command:
        return jsonify({"error": f"Invalid comparison method: {method}"}), 400

    mode = "local" if is_local else "upload"
    logging.info(f"Running FFMPEG command ({mode}): {' '.join(ffmpeg_command)}")
    process = subprocess.run(ffmpeg_command, capture_output=True, text=True, check=False)

    # Handle FFMPEG Result
    if process.returncode != 0:
        error_message = f"FFMPEG failed ({mode} method: {method}). Code: {process.returncode}. Error: {process.stderr}"
        logging.error(error_message)
        logging.error(f"Failed command: {' '.join(ffmpeg_command)}") # Log the exact command
        return jsonify({"error": f"Video processing failed ({mode}). Check server logs. Details: {process.stderr[:500]}..."}), 500
    else:
        logging.info(f"FFMPEG processing successful ({mode} method: {method}). Output: {output_path}")
        output_url = f"/outputs/{output_filename}"
        return jsonify({"output_url": output_url, "output_filename": output_filename}), 200


@app.route('/compare', methods=['POST'])
def compare_videos():
    """Handles video uploads, runs comparison, returns result path. Cleans up uploads."""
    logging.info("Received request to /compare (upload)")
    input1_path, input2_path = None, None
    files_to_cleanup = []

    try:
        # Validate request parts
        if 'video1' not in request.files or 'video2' not in request.files:
            return jsonify({"error": "Missing video file(s) in request"}), 400
        if 'comparison_method' not in request.form or 'playback_speed' not in request.form:
             return jsonify({"error": "Missing 'comparison_method' or 'playback_speed' in request form"}), 400

        video1 = request.files['video1']
        video2 = request.files['video2']
        method = request.form['comparison_method']
        speed = request.form['playback_speed']

        # Validate files
        if video1.filename == '' or video2.filename == '':
            return jsonify({"error": "No selected file or empty filename"}), 400
        if not (allowed_file(video1.filename) and allowed_file(video2.filename)):
            # Log the actual filename and extension for debugging
            logging.warning(f"Invalid file type submitted. Files: {video1.filename}, {video2.filename}. Allowed: {ALLOWED_EXTENSIONS}")
            return jsonify({"error": "Invalid file type. Allowed: " + ", ".join(ALLOWED_EXTENSIONS)}), 400

        # Save Uploaded Files
        unique_id = str(uuid.uuid4())
        ext1 = video1.filename.rsplit('.', 1)[1].lower() if '.' in video1.filename else ''
        ext2 = video2.filename.rsplit('.', 1)[1].lower() if '.' in video2.filename else ''
        input1_filename = f"{unique_id}_1.{ext1}" if ext1 else f"{unique_id}_1"
        input2_filename = f"{unique_id}_2.{ext2}" if ext2 else f"{unique_id}_2"
        input1_path = os.path.join(app.config['UPLOAD_FOLDER'], input1_filename)
        input2_path = os.path.join(app.config['UPLOAD_FOLDER'], input2_filename)

        files_to_cleanup.extend([input1_path, input2_path]) # Mark for cleanup
        video1.save(input1_path)
        video2.save(input2_path)
        logging.info(f"Saved input videos: {input1_path}, {input2_path}")

        # Process and get response
        return process_request(method, input1_path, input2_path, speed, is_local=False)

    except Exception as e:
        logging.exception("An unexpected error occurred during /compare request.")
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500
    finally:
        # Cleanup Uploaded Files
        cleanup_files(files_to_cleanup)
        logging.info("Cleanup attempt finished for upload request.")


@app.route('/compare_local', methods=['POST'])
def compare_local_videos():
    """Runs comparison using predefined local files. Expects JSON body."""
    logging.info("Received request to /compare_local (quick test)")
    try:
        # Validate request JSON
        data = request.get_json()
        if not data or 'comparison_method' not in data or 'playback_speed' not in data:
             return jsonify({"error": "Missing 'comparison_method' or 'playback_speed' in request JSON body"}), 400

        method = data['comparison_method']
        speed = data['playback_speed']
        input1_path = QUICK_TEST_FILE_1
        input2_path = QUICK_TEST_FILE_2

        # Check if predefined files exist
        if not os.path.exists(input1_path) or not os.path.exists(input2_path):
            logging.error(f"Quick test files not found: {input1_path}, {input2_path}")
            return jsonify({"error": f"Sample files not found on server at {input1_path} and {input2_path}"}), 404

        logging.info(f"Using local files for quick test: {input1_path}, {input2_path}")

        # Process and get response
        return process_request(method, input1_path, input2_path, speed, is_local=True)

    except Exception as e:
        logging.exception("An unexpected error occurred during /compare_local request.")
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500
    # No finally/cleanup needed for local files


# --- Static File Serving ---

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
       return send_from_directory('.', 'index.html') # Ensure this matches your HTML file
    except FileNotFoundError:
       logging.error("Frontend HTML file 'index.html' not found in the current directory.")
       return "Error: Frontend HTML file not found.", 404


# --- Main Execution ---
if __name__ == '__main__':
    create_directories()
    # Check for quick test files on startup
    if not os.path.exists(QUICK_TEST_FILE_1) or not os.path.exists(QUICK_TEST_FILE_2):
         logging.warning(f"Quick test sample files not found: {QUICK_TEST_FILE_1}, {QUICK_TEST_FILE_2}. The 'Quick Test' button will result in an error.")

    app.run(host='0.0.0.0', port=5000, debug=True) # Debug=False in production!
