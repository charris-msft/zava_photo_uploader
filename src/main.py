"""
FastAPI Photo Uploader
A FastAPI application for uploading photos to local filesystem storage.
"""

import os
import uuid
import logging
import platform
import mimetypes
from typing import List, Optional
from datetime import datetime
from pathlib import Path

import json
import aiofiles
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def safe_log(level: str, message: str, emoji: str = "", alt_prefix: str = ""):
    """Log with emoji on non-Windows systems, plain text on Windows"""
    if platform.system() == 'Windows':
        prefix = f"[{alt_prefix}]" if alt_prefix else ""
        getattr(logger, level.lower())(f"{prefix} {message}")
    else:
        getattr(logger, level.lower())(f"{emoji} {message}")

# Configuration
class Config:
    """Application configuration for local filesystem storage"""

    def __init__(self):
        self.upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads"))
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
        self.allowed_mime_types = {
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'image/bmp', 'image/tiff'
        }

config = Config()

# Initialize FastAPI app
app = FastAPI(
    title="🖼️ Photo Uploader",
    description="A FastAPI application for uploading photos to local filesystem storage",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware for development (configure appropriately for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Add your frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class LocalPhotoUploader:
    """Photo uploader using local filesystem storage"""

    def __init__(self):
        self.config = config

    def _validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file"""
        file_extension = Path(file.filename or "").suffix.lower()
        if file_extension not in self.config.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{file_extension}' not allowed. "
                       f"Allowed types: {', '.join(self.config.allowed_extensions)}"
            )

        if file.content_type not in self.config.allowed_mime_types:
            raise HTTPException(
                status_code=400,
                detail=f"MIME type '{file.content_type}' not allowed"
            )

    def _generate_filename(self, original_filename: str) -> str:
        """Generate a unique filename in timestamp_cleanname_uuid8.ext format"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_extension = Path(original_filename).suffix.lower()
        unique_id = str(uuid.uuid4())[:8]
        clean_name = "".join(
            c for c in Path(original_filename).stem if c.isalnum() or c in ('-', '_')
        )
        clean_name = clean_name[:20]
        return f"{timestamp}_{clean_name}_{unique_id}{file_extension}"

    async def upload_photo(self, file: UploadFile, tags: Optional[dict] = None) -> dict:
        """Write uploaded photo to the local upload directory"""
        try:
            self._validate_file(file)

            filename = self._generate_filename(file.filename or f"photo_{uuid.uuid4()}")
            dest_path = self.config.upload_dir / filename

            file_content = await file.read()
            file_size = len(file_content)

            if file_size > self.config.max_file_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {self.config.max_file_size // 1024 // 1024}MB"
                )

            if file_size == 0:
                raise HTTPException(status_code=400, detail="Empty file not allowed")

            async with aiofiles.open(dest_path, "wb") as f:
                await f.write(file_content)

            # Write metadata sidecar
            meta = {
                'original_filename': file.filename,
                'upload_timestamp': datetime.utcnow().isoformat(),
            }
            if tags:
                if tags.get('album'):
                    meta['album'] = tags['album']
                if tags.get('description'):
                    meta['description'] = tags['description']
            meta_path = self.config.upload_dir / (filename + '.meta.json')
            async with aiofiles.open(meta_path, 'w') as mf:
                await mf.write(json.dumps(meta))

            safe_log("info", f"Successfully uploaded photo: {filename} ({file_size} bytes)", "✅", "SUCCESS")

            return {
                'success': True,
                'filename': filename,
                'file_size': file_size,
                'content_type': file.content_type,
                'upload_timestamp': datetime.utcnow().isoformat(),
                'album': meta.get('album', ''),
            }

        except HTTPException:
            raise
        except Exception as e:
            safe_log("error", f"Unexpected error during upload: {e}", "❌", "ERROR")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
        finally:
            await file.seek(0)

    async def list_photos(self, limit: int = 50) -> List[dict]:
        """List photos by reading the upload directory, sorted by mtime descending"""
        try:
            entries = []
            for entry in self.config.upload_dir.iterdir():
                if entry.is_file() and entry.suffix.lower() in self.config.allowed_extensions:
                    stat = entry.stat()
                    content_type = mimetypes.guess_type(entry.name)[0] or 'application/octet-stream'

                    # Read sidecar metadata if present
                    meta = {}
                    meta_path = self.config.upload_dir / (entry.name + '.meta.json')
                    if meta_path.exists():
                        try:
                            with open(meta_path, 'r') as mf:
                                meta = json.load(mf)
                        except Exception:
                            pass

                    entries.append((stat.st_mtime, {
                        'name': entry.name,
                        'size': stat.st_size,
                        'last_modified': datetime.utcfromtimestamp(stat.st_mtime).isoformat(),
                        'content_type': content_type,
                        'url': f"/photos/{entry.name}",
                        'metadata': meta,
                    }))

            entries.sort(key=lambda x: x[0], reverse=True)
            photos = [item for _, item in entries[:limit]]

            safe_log("info", f"Listed {len(photos)} photos from local storage", "✅", "SUCCESS")
            return photos

        except Exception as e:
            safe_log("error", f"Error listing photos: {e}", "❌", "ERROR")
            raise HTTPException(status_code=500, detail=f"Failed to list photos: {str(e)}")

    async def get_photo_data(self, filename: str) -> tuple[bytes, str]:
        """Read a photo file and return its bytes and content type"""
        file_path = (self.config.upload_dir / filename).resolve()

        # Security: ensure resolved path stays within upload_dir
        if not str(file_path).startswith(str(self.config.upload_dir.resolve())):
            raise HTTPException(status_code=400, detail="Invalid filename")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Photo not found")

        try:
            async with aiofiles.open(file_path, "rb") as f:
                content = await f.read()

            content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            safe_log("info", f"Retrieved photo: {filename} ({len(content)} bytes)", "✅", "SUCCESS")
            return content, content_type

        except HTTPException:
            raise
        except Exception as e:
            safe_log("error", f"Error retrieving photo {filename}: {e}", "❌", "ERROR")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve photo: {str(e)}")

    async def delete_photo(self, filename: str) -> bool:
        """Delete a photo file from the upload directory"""
        file_path = (self.config.upload_dir / filename).resolve()

        # Security: ensure resolved path stays within upload_dir
        if not str(file_path).startswith(str(self.config.upload_dir.resolve())):
            raise HTTPException(status_code=400, detail="Invalid filename")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Photo not found")

        try:
            file_path.unlink()
            safe_log("info", f"Successfully deleted photo: {filename}", "✅", "SUCCESS")
            return True

        except Exception as e:
            safe_log("error", f"Error deleting photo {filename}: {e}", "❌", "ERROR")
            raise HTTPException(status_code=500, detail=f"Failed to delete photo: {str(e)}")

# Initialize the photo uploader
photo_uploader = LocalPhotoUploader()

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with photo upload form"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_photo(
    request: Request,
    file: UploadFile = File(...),
    album: str = Form(""),
    description: str = Form("")
):
    """Upload photo endpoint"""
    try:
        tags = {}
        if album:
            tags['album'] = album
        if description:
            tags['description'] = description

        result = await photo_uploader.upload_photo(file, tags=tags)

        return templates.TemplateResponse("upload_success.html", {
            "request": request,
            "result": result,
            "filename": file.filename
        })

    except HTTPException as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": e.detail,
            "status_code": e.status_code
        })
    except Exception as e:
        safe_log("error", f"Unexpected error in upload endpoint: {e}", "❌", "ERROR")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "An unexpected error occurred",
            "status_code": 500
        })

@app.get("/api/photos")
async def get_photos(limit: int = 50):
    """API endpoint to get photos list"""
    photos = await photo_uploader.list_photos(limit=limit)
    return JSONResponse({"photos": photos, "count": len(photos)})

@app.get("/photos/{filename}")
async def get_photo_image(filename: str):
    """Serve a photo image by filename"""
    try:
        content, content_type = await photo_uploader.get_photo_data(filename)
        return Response(content=content, media_type=content_type)
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", f"Error serving image {filename}: {e}", "❌", "ERROR")
        raise HTTPException(status_code=500, detail="Failed to serve image")

@app.get("/gallery", response_class=HTMLResponse)
async def photo_gallery(request: Request, limit: int = 200):
    """Photo gallery page grouped by album"""
    try:
        photos = await photo_uploader.list_photos(limit=limit)

        # Group by album; named albums sorted alphabetically, Uncategorized last
        grouped: dict = {}
        for photo in photos:
            album = (photo.get('metadata') or {}).get('album', '').strip() or 'Uncategorized'
            grouped.setdefault(album, []).append(photo)

        albums = dict(
            sorted(grouped.items(), key=lambda x: (x[0] == 'Uncategorized', x[0].lower()))
        )

        return templates.TemplateResponse("gallery.html", {
            "request": request,
            "photos": photos,
            "albums": albums,
            "photos_json": json.dumps(photos),
        })
    except Exception as e:
        safe_log("error", f"Error loading gallery: {e}", "❌", "ERROR")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load photo gallery",
            "status_code": 500
        })

@app.delete("/api/photos/{filename}")
async def delete_photo_endpoint(filename: str):
    """API endpoint to delete a photo"""
    success = await photo_uploader.delete_photo(filename)
    return JSONResponse({"success": success, "message": f"Photo {filename} deleted successfully"})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        upload_dir = config.upload_dir.resolve()
        writable = os.access(upload_dir, os.W_OK)
        return {
            "status": "healthy" if writable else "degraded",
            "upload_dir": str(upload_dir),
            "upload_dir_writable": writable,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        safe_log("error", f"Health check failed: {e}", "❌", "ERROR")
        return {"status": "unhealthy", "error": str(e), "timestamp": datetime.utcnow().isoformat()}

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error": "Page not found",
        "status_code": 404
    })

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    safe_log("error", f"Internal server error: {exc}", "❌", "ERROR")
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error": "Internal server error",
        "status_code": 500
    })

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
