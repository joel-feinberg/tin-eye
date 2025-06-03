Video Comparison Tool
=====================

A web application to compare two videos using various FFMPEG-based methods.

Description
-----------

This tool allows users to upload two video files (MP4, MOV, AVI, MKV, WebM) through a web interface. The backend, built with Flask, processes these videos using FFMPEG to create a single output video comparing the two inputs based on a selected method. The resulting comparison video is then displayed back to the user in the browser at a selectable playback speed.

This is particularly useful for visualizing differences between versions of animations or simulations, such as comparing outputs from different iterations of an IK/physics model applied to motion capture data.

Features
--------

-   **Multiple Comparison Methods:**

    -   Side-by-Side (Horizontal Stack)

    -   Vertical Stack

    -   Difference Blend (with brightness boost & subtle input tinting)

    -   Subtract Blend (with brightness boost & subtle input tinting)

    -   Opacity Blend (50% Average Blend, with subtle input tinting)

    -   Interleave (Blinking effect using frame overlay)

    -   Color Channel Mix (R from Video 1, G averaged, B from Video 2)

-   **Playback Speed Control:** Output video can be generated at Normal (1x), Half (0.5x - Default), or Quarter (0.25x) speed.

-   **File Upload:** Supports MP4, MOV, AVI, MKV, and WebM formats.

-   **Quick Test Feature:** Allows testing with pre-named local files (`uploads/old.mp4` and `uploads/new.mp4`) without manual uploads.

-   **Web Interface:** Simple UI for uploading files, selecting options, and viewing results.

-   **Backend Processing:** Uses Python (Flask) and FFMPEG.

-   **Temporary File Cleanup:** Automatically removes uploaded files after processing.

Prerequisites
-------------

Before running the application, ensure you have the following installed:

1.  **Python 3:** Download from [python.org](https://www.python.org/downloads/ "null")

2.  **Flask:** Python web framework. Install via pip:

    ```
    pip install Flask

    ```

3.  **FFMPEG:** A complete, cross-platform solution to record, convert and stream audio and video. Download from [ffmpeg.org](https://ffmpeg.org/download.html "null").

    -   **Important:** Ensure the `ffmpeg` command is accessible from your system's command line (i.e., it's in your system's PATH environment variable). You can test this by typing `ffmpeg -version` in your terminal or command prompt.

Installation
------------

1.  Clone this repository:

    ```
    git clone <your-repo-url>
    cd <repository-directory>

    ```

2.  (Optional, Recommended) Create and activate a virtual environment:

    ```
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`

    ```

3.  Install the required Python package:

    ```
    pip install Flask

    ```

Running the Application
-----------------------

### Option 1: Using the Setup Script (Recommended)

1.  Make the setup script executable:

    ```
    chmod +x setup_and_run.sh
    ```

2.  Run the setup script:

    ```
    ./setup_and_run.sh
    ```

    This script will automatically:
    - Check for FFMPEG installation
    - Set up a Python virtual environment
    - Install required packages
    - Create necessary directories
    - Start the Flask application
    - Open your web browser to the application
    - Handle cleanup when you're done (press Ctrl+C to exit)

3.  **(Optional Quick Test Setup):** If you want to use the "Quick Test" button, place two video files named exactly `old.mp4` and `new.mp4` inside the `uploads/` directory before running the script.

### Option 2: Manual Setup

1.  Ensure all prerequisites are met (Python, Flask installed, FFMPEG installed and in PATH).

2.  Navigate to the project directory containing `app.py` and `index.html`.

3.  **(Optional Quick Test Setup):** If you want to use the "Quick Test" button, place two video files named exactly `old.mp4` and `new.mp4` inside the `uploads/` directory (you may need to create this directory first if it doesn't exist).

4.  Run the Flask development server:

    ```
    python app.py
    ```

5.  The application will start, and you should see output similar to:

    ```
     * Running on http://127.0.0.1:5000
     * Running on http://<your-local-ip>:5000
    ```

6.  Open your web browser and go to `http://127.0.0.1:5000` or `http://localhost:5000`.

How to Use
----------

1.  Access the web application in your browser.

2.  **Option A: Upload Files**

    -   Click "Choose File" for "Video 1" and select your first video file (mp4, mov, avi, mkv, webm).

    -   Click "Choose File" for "Video 2" and select your second video file.

    -   Select the desired "Comparison Method" from the dropdown.

    -   Select the desired "Playback Speed" from the dropdown (defaults to Half Speed).

    -   Click the "Generate Comparison from Uploads" button.

3.  **Option B: Quick Test (Requires Setup)**

    -   Ensure `uploads/old.mp4` and `uploads/new.mp4` exist on the server (see Running the Application, step 3).

    -   Select the desired "Comparison Method" from the dropdown.

    -   Select the desired "Playback Speed" from the dropdown (defaults to Half Speed).

    -   Click the "Quick Test with Samples (old.mp4 / new.mp4)" button.

4.  Wait for the processing to complete. Status messages ("Uploading...", "Processing...") will be displayed.

5.  Once finished, the comparison video will appear in the player below, and a download link will be available.

File Structure
--------------

```
.
├── app.py           # Flask backend logic
├── index.html       # Frontend HTML, CSS (Tailwind via CDN), and JavaScript
├── setup_and_run.sh # Automated setup and run script
├── uploads/         # Directory for uploaded videos & quick test samples (created automatically)
├── outputs/         # Directory for generated comparison videos (created automatically)
└── README.md        # This file
```

Future Work / Potential Enhancements
------------------------------------

-   Implement more advanced comparison methods (e.g., Heatmaps using OpenCV).

-   Add interactive controls (e.g., slider for opacity blend).

-   Improve progress reporting for long processing times (e.g., using WebSockets or polling).

-   Optimize for very large file uploads (chunking, direct-to-storage).

-   Implement asynchronous task queues (e.g., Celery) for better scalability and non-blocking processing.

-   Add user authentication and job history/management.

-   Improve error handling and user feedback granularity.

-   Allow customization of FFMPEG parameters (resolution, quality, tinting amount, boost amount).

-   Containerize the application using Docker for easier deployment.

-   Add unit and integration tests.