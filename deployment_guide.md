# Google Cloud Run Deployment Guide

## Prerequisites
1. **Google Cloud Account** with billing enabled
2. **Google Cloud CLI** installed and authenticated
3. **Docker** installed locally (for testing)
4. **Project ID** ready for deployment

## Quick Start Commands

### 1. Set up Google Cloud Project
```bash
# Set your project ID
export PROJECT_ID=your-project-id
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2. Build and Deploy (Option A: Cloud Build)
```bash
# Deploy using Cloud Build (recommended)
gcloud builds submit --config cloudbuild.yaml .
```

### 3. Build and Deploy (Option B: Manual)
```bash
# Build container locally
docker build -t gcr.io/$PROJECT_ID/video-comparison-tool .

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/video-comparison-tool

# Deploy to Cloud Run
gcloud run deploy video-comparison-tool \
  --image gcr.io/$PROJECT_ID/video-comparison-tool \
  --region us-central1 \
  --platform managed \
  --memory 1Gi \
  --cpu 1 \
  --timeout 900 \
  --concurrency 10 \
  --max-instances 3 \
  --allow-unauthenticated
```

### 4. Test Local Docker Build
```bash
# Build locally
docker build -t video-comparison-local .

# Run locally
docker run -p 8080:8080 -e PORT=8080 video-comparison-local

# Test health endpoint
curl http://localhost:8080/health
```

## Configuration Options

### Environment Variables
- `PORT`: Port number (default: 8080, set by Cloud Run)
- `FLASK_ENV`: Set to 'development' for debug mode

### Cloud Run Settings
- **Memory**: 1Gi (recommended for video processing)
- **CPU**: 1 vCPU (can increase for better performance)
- **Timeout**: 900 seconds (15 minutes for video processing)
- **Concurrency**: 10 (concurrent requests per instance)
- **Max Instances**: 3 (cost control)

## Important Notes

### Storage Limitations
- **Ephemeral Storage**: Files are lost when container restarts
- **Upload/Output**: Stored temporarily in container filesystem
- **Recommendation**: For production, consider Google Cloud Storage integration

### Performance Considerations
- **Cold Starts**: Initial requests may be slower
- **Video Processing**: CPU-intensive, may need higher specs
- **Memory Usage**: FFMPEG can be memory-intensive

### Security
- **Authentication**: Currently allows unauthenticated access
- **File Uploads**: No size limits configured (consider adding)
- **Rate Limiting**: Not implemented (consider adding)

## Troubleshooting

### Common Issues
1. **Build Failures**: Check Dockerfile syntax and dependencies
2. **FFMPEG Not Found**: Ensure Ubuntu base image and apt install
3. **Memory Errors**: Increase memory allocation in Cloud Run
4. **Timeout Errors**: Increase timeout or optimize video processing

### Logs and Monitoring
```bash
# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Stream logs in real-time
gcloud logging tail "resource.type=cloud_run_revision"
```

## File Structure After Deployment
```
tin-eye/
├── Dockerfile                 # Container definition
├── cloudbuild.yaml           # Cloud Build configuration
├── requirements.txt          # Python dependencies
├── .dockerignore            # Docker build exclusions
├── app.py                   # Modified Flask app (production-ready)
├── index.html              # Frontend
├── deployment_guide.md     # This guide
└── uploads/                # Ephemeral storage
    └── outputs/           # Generated videos
```

## Next Steps
1. Test Docker build locally
2. Deploy to Cloud Run
3. Verify functionality
4. Consider adding persistent storage (Cloud Storage)
5. Add monitoring and alerting
6. Implement authentication if needed
