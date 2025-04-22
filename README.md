# Video Comparison Tool (MVP)
A simple web application to compare two videos side-by-side using FFMPEG. This is the Minimum Viable Product (MVP) version.
## Description
This tool allows users to upload two video files through a web interface. The backend, built with Flask, processes these videos using FFMPEG to create a single output video showing the two inputs stacked horizontally (side-by-side). The resulting comparison video is then displayed back to the user in the browser.
This is particularly useful for visualizing differences between versions of animations or simulations, such as comparing outputs from different iterations of an IK/physics model applied to motion capture data.
## Prerequisites
Before running the application, ensure you have the following installed:
1. Python 3: Download from python.org
2. Flask: Python web framework. Install via pip:
```pip install Flask```

3. FFMPEG: A complete, cross-platform solution to record, convert and stream audio and video. Download from ffmpeg.org.
- Important: Ensure the ffmpeg command is accessible from your system's command line (i.e., it's in your system's PATH environment variable). You can test this by typing ffmpeg -version in your terminal or command prompt.
## Installation
Clone or download this repository/code.
Navigate to the project directory in your terminal.
Install the required Python package:
pip install Flask


## Running the Application
Ensure all prerequisites are met (Python, Flask installed, FFMPEG installed and in PATH).
Navigate to the project directory containing app.py and index.html.
Run the Flask development server:
python app.py


The application will start, and you should see output similar to:
 * Running on http://127.0.0.1:5000
 * Running on http://<your-local-ip>:5000


Open your web browser and go to http://127.0.0.1:5000 or http://localhost:5000.

## How to Use
1. Access the web application in your browser.
2. Click the "Choose File" button for "Video 1" and select your first 3. video file.
3. Click the "Choose File" button for "Video 2" and select your second video file.
4. Click the "Generate Comparison" button.
5. Wait for the processing to complete. Status messages ("Uploading...", "Processing...") will be displayed.
6. Once finished, the side-by-side comparison video will appear in the player below, and a download link will be available.

## File Structure
```
.
├── app.py           # Flask backend logic
├── index.html       # Frontend HTML, CSS (Tailwind via CDN), and JavaScript
├── uploads/         # Temporary directory for uploaded videos (created automatically)
├── outputs/         # Directory for generated comparison videos (created automatically)
└── README.md        # This file
```

## Current Features (MVP)
- Upload two video files via web UI.
- Backend processing using FFMPEG.
- Generates a side-by-side (horizontal stack) comparison video.
- Displays the resulting video in the browser.
- Provides a download link for the result.
- Basic status updates and error handling.
- Cleans up temporary uploaded files.
## Future Work / Potential Enhancements
- Add more comparison methods (Opacity Blend, Difference Blend, Heatmaps).
- Improve progress reporting for long processing times (e.g., using WebSockets or polling).
- Optimize for large file uploads (chunking).
- Implement asynchronous task queues (e.g., Celery) for better scalability and non-blocking processing.
- Add user authentication and job history.
- Improve error handling and user feedback.
- Allow customization of FFMPEG parameters (resolution, quality).
- Containerize the application using Docker.
