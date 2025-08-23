from PIL import Image
import io
import os

def preprocess_image(image_path: str, max_size: int = 1024, quality: int = 70) -> str:
    """
    Preprocess image to reduce size while maintaining OCR quality.
    Returns path to processed image.
    """
    processed_path = image_path.replace('.', '_processed.')
    
    with Image.open(image_path) as img:
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Resize if too large
        width, height = img.size
        if max(width, height) > max_size:
            ratio = max_size / max(width, height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save with compression
        img.save(processed_path, 'JPEG', quality=quality, optimize=True)
    
    return processed_path

def get_image_info(image_path: str) -> dict:
    """Get basic image information for debugging."""
    if not os.path.exists(image_path):
        return {}
    
    file_size = os.path.getsize(image_path)
    with Image.open(image_path) as img:
        return {
            'size': f"{img.width}x{img.height}",
            'file_size': f"{file_size // 1024}KB",
            'format': img.format
        }