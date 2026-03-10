/**
 * Photo Uploader JavaScript - Enhanced UI interactions
 */

// Global state
let currentFile = null;
let isUploading = false;

// DOM elements - initialized in init() function
let fileInput = null;
let dropZone = null;
let filePreview = null;
let previewImage = null;
let fileName = null;
let fileSize = null;
let removeFileBtn = null;
let uploadForm = null;
let submitBtn = null;
let progressContainer = null;
let progressBar = null;
let progressText = null;

// File size formatter
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Show notification
function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} mr-2"></i>
        ${message}
    `;
    
    document.body.appendChild(notification);
    
    // Trigger animation
    requestAnimationFrame(() => {
        notification.classList.add('show');
    });
    
    // Remove notification
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, duration);
}

// Validate file
function validateFile(file) {
    const maxSize = 100 * 1024 * 1024; // 100MB
    const allowedTypes = [
        'image/jpeg', 'image/png', 'image/gif', 
        'image/webp', 'image/bmp', 'image/tiff'
    ];
    
    if (!allowedTypes.includes(file.type)) {
        throw new Error(`File type "${file.type}" is not allowed. Please upload an image file.`);
    }
    
    if (file.size > maxSize) {
        throw new Error(`File size ${formatFileSize(file.size)} exceeds the 100MB limit.`);
    }
    
    if (file.size === 0) {
        throw new Error('Cannot upload empty file.');
    }
    
    return true;
}

// Display file preview
function displayFilePreview(file) {
    try {
        validateFile(file);
        
        if (fileName) fileName.textContent = file.name;
        if (fileSize) fileSize.textContent = formatFileSize(file.size);
        
        // Create image preview
        if (previewImage && filePreview) {
            const reader = new FileReader();
            reader.onload = function(e) {
                previewImage.src = e.target.result;
                previewImage.alt = file.name;
                filePreview.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        }
        
        currentFile = file;
        updateSubmitButton();
        
    } catch (error) {
        showNotification(error.message, 'error');
        clearFilePreview();
    }
}

// Clear file preview
function clearFilePreview() {
    if (filePreview) filePreview.classList.add('hidden');
    if (previewImage) previewImage.src = '';
    if (fileName) fileName.textContent = '';
    if (fileSize) fileSize.textContent = '';
    if (fileInput) fileInput.value = '';
    currentFile = null;
    updateSubmitButton();
}

// Update submit button state
function updateSubmitButton() {
    if (!submitBtn) return;
    
    if (isUploading) {
        submitBtn.disabled = true;
        submitBtn.classList.add('btn-loading');
        submitBtn.innerHTML = '<i class="fas fa-spinner animate-spin mr-2"></i>Uploading...';
    } else if (currentFile) {
        submitBtn.disabled = false;
        submitBtn.classList.remove('btn-loading');
        submitBtn.innerHTML = '<i class="fas fa-upload mr-2"></i>Upload Photo';
    } else {
        submitBtn.disabled = true;
        submitBtn.classList.remove('btn-loading');
        submitBtn.innerHTML = '<i class="fas fa-upload mr-2"></i>Select a photo first';
    }
}

// Handle drag and drop
function setupDragAndDrop() {
    if (!dropZone) return;
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop zone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });
    
    // Handle dropped files
    dropZone.addEventListener('drop', handleDrop, false);
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight() {
        if (dropZone) dropZone.classList.add('drag-over');
    }
    
    function unhighlight() {
        if (dropZone) dropZone.classList.remove('drag-over');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            const file = files[0];
            if (fileInput) fileInput.files = files; // Update the input
            displayFilePreview(file);
        }
    }
}

// Handle file input change
function setupFileInput() {
    if (!fileInput) return;
    
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            displayFilePreview(file);
        }
    });
}

// Handle remove file
function setupRemoveFile() {
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', clearFilePreview);
    }
}

// Setup form submission with progress
function setupFormSubmission() {
    if (uploadForm) {
        uploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!currentFile || isUploading) {
                return;
            }
            
            try {
                isUploading = true;
                updateSubmitButton();
                showProgress();
                
                // Create FormData
                const formData = new FormData(uploadForm);
                
                // Submit with fetch to handle progress
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    // Success - the server will redirect or return success page
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('text/html')) {
                        // Server returned HTML (success page)
                        document.body.innerHTML = await response.text();
                    } else {
                        // JSON response
                        const result = await response.json();
                        showNotification('Photo uploaded successfully!', 'success');
                        setTimeout(() => {
                            window.location.href = '/gallery';
                        }, 1500);
                    }
                } else {
                    const error = await response.text();
                    throw new Error(error || 'Upload failed');
                }
                
            } catch (error) {
                console.error('Upload error:', error);
                showNotification('Upload failed: ' + error.message, 'error');
            } finally {
                isUploading = false;
                hideProgress();
                updateSubmitButton();
            }
        });
    }
}

// Show upload progress
function showProgress() {
    if (progressContainer) {
        progressContainer.classList.remove('hidden');
        // Simulate progress since we can't get real progress with form submission
        animateProgress();
    }
}

// Hide upload progress
function hideProgress() {
    if (progressContainer) {
        progressContainer.classList.add('hidden');
        if (progressBar) progressBar.style.width = '0%';
        if (progressText) progressText.textContent = 'Uploading...';
    }
}

// Animate progress bar
function animateProgress() {
    if (!progressBar || !progressText) return;
    
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress >= 90) {
            progress = 90; // Stay at 90% until actual completion
            clearInterval(interval);
        }
        progressBar.style.width = progress + '%';
        progressText.textContent = `Uploading... ${Math.round(progress)}%`;
    }, 200);
    
    // Store interval reference to clear it later if needed
    window.uploadProgressInterval = interval;
}

// Complete progress
function completeProgress() {
    if (window.uploadProgressInterval) {
        clearInterval(window.uploadProgressInterval);
    }
    if (progressBar) progressBar.style.width = '100%';
    if (progressText) progressText.textContent = 'Upload complete!';
}

// Setup keyboard shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + U for upload (when no file selected)
        if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
            e.preventDefault();
            if (!currentFile) {
                fileInput.click();
            }
        }
        
        // Escape to clear file
        if (e.key === 'Escape' && currentFile) {
            clearFilePreview();
        }
        
        // Enter to submit (when form is focused)
        if (e.key === 'Enter' && document.activeElement.form === uploadForm && currentFile) {
            e.preventDefault();
            uploadForm.dispatchEvent(new Event('submit'));
        }
    });
}

// Setup accessibility enhancements
function setupAccessibility() {
    // Add ARIA labels
    if (dropZone) {
        dropZone.setAttribute('role', 'button');
        dropZone.setAttribute('aria-label', 'Click or drag to upload photo');
        dropZone.setAttribute('tabindex', '0');
        
        // Handle keyboard activation
        dropZone.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                fileInput.click();
            }
        });
    }
    
    // Announce file selection to screen readers
    if (fileInput) {
        fileInput.setAttribute('aria-describedby', 'file-help');
    }
}

// Setup tooltips (simple implementation)
function setupTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(element => {
        element.addEventListener('mouseenter', function() {
            const tooltip = document.createElement('div');
            tooltip.className = 'absolute z-50 px-2 py-1 text-xs text-white bg-gray-800 rounded shadow-lg';
            tooltip.textContent = this.getAttribute('data-tooltip');
            tooltip.style.top = '100%';
            tooltip.style.left = '50%';
            tooltip.style.transform = 'translateX(-50%)';
            tooltip.style.marginTop = '4px';
            
            this.style.position = 'relative';
            this.appendChild(tooltip);
            this._tooltip = tooltip;
        });
        
        element.addEventListener('mouseleave', function() {
            if (this._tooltip) {
                this.removeChild(this._tooltip);
                this._tooltip = null;
            }
        });
    });
}

// Initialize the application
function init() {
    // Initialize DOM elements
    fileInput = document.getElementById('file');
    dropZone = document.getElementById('dropZone');
    filePreview = document.getElementById('filePreview');
    previewImage = document.getElementById('previewImage');
    fileName = document.getElementById('fileName');
    fileSize = document.getElementById('fileSize');
    removeFileBtn = document.getElementById('removeFile');
    uploadForm = document.getElementById('uploadForm');
    submitBtn = document.getElementById('submitBtn');
    progressContainer = document.getElementById('progressContainer');
    progressBar = document.getElementById('progressBar');
    progressText = document.getElementById('progressText');

    // Only initialize if we're on the upload page
    if (uploadForm) {
        setupDragAndDrop();
        setupFileInput();
        setupRemoveFile();
        setupFormSubmission();
        setupKeyboardShortcuts();
        setupAccessibility();
        setupTooltips();
        updateSubmitButton();
        
        console.log('📸 Photo Uploader initialized successfully');
        
        // Add some helpful console messages
        console.log('💡 Tips:');
        console.log('  - Drag and drop files onto the upload area');
        console.log('  - Press Ctrl/Cmd + U to select a file');
        console.log('  - Press Escape to clear the current file');
        console.log('  - Maximum file size: 100MB');
        console.log('  - Supported formats: JPG, PNG, GIF, WebP, BMP, TIFF');
    }
}

// Run initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Export functions for potential external use
window.PhotoUploader = {
    showNotification,
    formatFileSize,
    validateFile,
    clearFilePreview
};