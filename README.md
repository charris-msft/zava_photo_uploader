# 🖼️ Photo Uploader

A local FastAPI web application for uploading and managing photos on your computer.

## ✨ Features

- **Drag & Drop Upload** - Intuitive file upload interface
- **Real-time Progress** - Visual upload feedback
- **Photo Gallery** - Browse and manage uploaded photos
- **Responsive Design** - Works on desktop and mobile
- **REST API** - OpenAPI documentation included

## 🚀 Quick Start

### Prerequisites

- Python 3.8+

### Run Locally

```powershell
# Run the setup script (handles everything automatically)
.\run.ps1
```

Or manually:

```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.example .env

# Start the application
cd src
python start.py
```

The app will be available at:
- **Main App**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **Gallery**: http://localhost:8000/gallery

## ⚙️ Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `UPLOAD_DIR` | Directory to store uploaded photos | `uploads` |
| `APP_HOST` | Host to bind to | `0.0.0.0` |
| `APP_PORT` | Port to listen on | `8000` |
| `APP_DEBUG` | Enable debug/reload mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

## 📁 File Structure

```
zava_photo_uploader/
├── src/
│   ├── main.py           # FastAPI application
│   ├── start.py          # Startup script
│   ├── templates/        # HTML templates
│   └── static/           # CSS & JavaScript
├── requirements.txt      # Python dependencies
├── run.ps1               # Local run script
└── .env.example          # Environment template
```

## 🧪 API

- `GET /` - Upload page
- `POST /upload` - Upload a photo
- `GET /api/photos` - List all photos (JSON)
- `GET /photos/{filename}` - Serve a photo
- `GET /gallery` - Photo gallery page
- `DELETE /api/photos/{filename}` - Delete a photo
- `GET /health` - Health check

## 📄 License

MIT License
