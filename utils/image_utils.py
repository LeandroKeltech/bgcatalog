import os
from PIL import Image
from kivymd.toast import toast

def capture_image():
    """
    Capture image using camera.
    Returns image path or None if cancelled/failed.
    """
    try:
        # This would use camera capture in actual implementation
        # For now, return None (no image captured)
        return None
    except Exception as e:
        toast(f"Camera error: {e}")
        return None

def compress_image(image_path, quality=85, max_size=(1024, 1024)):
    """
    Compress and resize image.
    Returns compressed image path or original path if failed.
    """
    try:
        if not os.path.exists(image_path):
            return image_path
        
        with Image.open(image_path) as img:
            # Resize if too large
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Compress and save
            compressed_path = image_path.replace('.jpg', '_compressed.jpg')
            img.save(compressed_path, 'JPEG', quality=quality, optimize=True)
            
            return compressed_path
    except Exception as e:
        toast(f"Image compression failed: {e}")
        return image_path

def get_app_image_dir():
    """
    Get app's private image directory.
    Creates directory if it doesn't exist.
    """
    try:
        # In actual implementation, this would be the app's private directory
        img_dir = os.path.join(os.getcwd(), 'images')
        os.makedirs(img_dir, exist_ok=True)
        return img_dir
    except Exception as e:
        toast(f"Image directory error: {e}")
        return os.getcwd()
