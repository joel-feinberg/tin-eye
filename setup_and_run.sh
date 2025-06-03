#!/bin/bash

# Video Comparison Tool Setup & Run Script
# This script automates the process of setting up and running the Video Comparison Tool.

# Terminal color codes for prettier output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored section headers
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print warning messages
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function to print error messages
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect the operating system
detect_os() {
    case "$(uname -s)" in
        Linux*)     OS="Linux";;
        Darwin*)    OS="macOS";;
        CYGWIN*|MINGW*|MSYS*) OS="Windows";;
        *)          OS="Unknown";;
    esac
    echo $OS
}

# Function to open browser based on operating system
open_browser() {
    local url=$1
    case $(detect_os) in
        "Linux")
            if command_exists xdg-open; then
                xdg-open "$url" &
            else
                print_warning "Could not automatically open browser. Please open $url manually."
            fi
            ;;
        "macOS")
            open "$url" &
            ;;
        "Windows")
            start "$url" &
            ;;
        *)
            print_warning "Unknown operating system. Please open $url manually."
            ;;
    esac
}

# Function to check if ffmpeg is installed
check_ffmpeg() {
    print_header "Checking FFMPEG"
    
    if command_exists ffmpeg; then
        print_success "FFMPEG is installed."
        ffmpeg -version | head -n 1
    else
        print_error "FFMPEG is not installed or not in PATH."
        print_error "Please install FFMPEG before continuing:"
        echo "  - Linux: sudo apt-get install ffmpeg"
        echo "  - macOS: brew install ffmpeg"
        echo "  - Windows: https://ffmpeg.org/download.html"
        return 1
    fi
    return 0
}

# Function to check and set up Python environment
setup_python() {
    print_header "Setting up Python Environment"
    
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3 and try again."
        echo "Download from: https://www.python.org/downloads/"
        return 1
    fi
    
    print_success "Python 3 is installed."
    python3 --version
    
    print_header "Creating Virtual Environment"
    
    # Create a virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created."
    else
        print_warning "Virtual environment already exists."
    fi
    
    # Activate the virtual environment
    case $(detect_os) in
        "Windows")
            source venv/Scripts/activate
            ;;
        *)
            source venv/bin/activate
            ;;
    esac
    
    print_success "Virtual environment activated."
    
    # Install required packages
    print_header "Installing Required Packages"
    pip install Flask
    
    print_success "Required packages installed."
    return 0
}

# Function to set up directory structure
setup_directories() {
    print_header "Setting up Directory Structure"
    
    # Create uploads and outputs directories
    if [ ! -d "uploads" ]; then
        mkdir -p uploads
        print_success "Created uploads directory."
    else
        print_warning "Uploads directory already exists."
    fi
    
    if [ ! -d "outputs" ]; then
        mkdir -p outputs
        print_success "Created outputs directory."
    else
        print_warning "Outputs directory already exists."
    fi
    
    return 0
}

# Function to run the Flask application
run_app() {
    print_header "Starting the Flask Application"
    
    # Check if Python script exists
    if [ ! -f "app.py" ]; then
        print_error "app.py not found. Make sure you're in the correct directory."
        return 1
    fi
    
    # Run the application in the background
    python3 app.py &
    app_pid=$!
    
    # Give the application a moment to start up
    sleep 2
    
    # Check if the process is still running
    if ps -p $app_pid > /dev/null; then
        print_success "Application is running at http://localhost:5000"
        
        # Store PID for cleanup
        echo "$app_pid" > .app_pid
        
        # Open the browser
        print_header "Opening Web Browser"
        open_browser "http://localhost:5000"
        
        print_header "Quick Test Options"
        # Check if quick test files exist
        if [ -f "uploads/old.mp4" ] && [ -f "uploads/new.mp4" ]; then
            print_success "Quick test sample files are available."
            print_success "The 'Quick Test' button will work on the web interface."
        else
            print_warning "Quick test sample files not found."
            print_warning "To enable the 'Quick Test' button, place two video files named:"
            echo "  - 'old.mp4' and 'new.mp4' in the 'uploads' directory."
        fi
        
        print_header "Application Running"
        echo "The application is now running in the background."
        echo "Press Ctrl+C to stop the application and clean up."
        
        # Set up a trap to handle Ctrl+C
        trap cleanup INT
        
        # Wait for user to press Ctrl+C
        while true; do
            sleep 1
        done
    else
        print_error "Failed to start the application. Check the logs for errors."
        return 1
    fi
    
    return 0
}

# Function to clean up when the script is terminated
cleanup() {
    print_header "Cleaning up"
    
    # Kill the Flask application
    if [ -f ".app_pid" ]; then
        app_pid=$(cat .app_pid)
        if ps -p $app_pid > /dev/null; then
            kill $app_pid
            print_success "Application stopped."
        fi
        rm .app_pid
    fi
    
    # Deactivate the virtual environment
    deactivate 2>/dev/null
    print_success "Virtual environment deactivated."
    
    print_success "Cleanup completed."
    exit 0
}

# Main function
main() {
    print_header "Video Comparison Tool Setup & Run Script"
    
    # Check for FFMPEG
    check_ffmpeg || return 1
    
    # Set up Python environment
    setup_python || return 1
    
    # Set up directory structure
    setup_directories || return 1
    
    # Run the application
    run_app || return 1
    
    return 0
}

# Run the main function
main

# If we get here, something went wrong
print_error "The setup and run process failed. Please check the error messages above."
exit 1
