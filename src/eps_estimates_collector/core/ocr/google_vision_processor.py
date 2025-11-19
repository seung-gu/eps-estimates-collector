"""Module for image OCR processing using Google Cloud Vision API."""

from pathlib import Path
import os
import cv2
import numpy as np
from dotenv import load_dotenv

try:
    from google.cloud import vision
    from google.oauth2 import service_account
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False

load_dotenv()


def get_google_vision_client():
    """Returns Google Cloud Vision client."""
    if not GOOGLE_VISION_AVAILABLE:
        raise ImportError("google-cloud-vision is not installed.")
    
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path or not Path(creds_path).exists():
        raise ValueError(f"Google Cloud Vision authentication file not found: {creds_path}")
    
    credentials = service_account.Credentials.from_service_account_file(creds_path)
    return vision.ImageAnnotatorClient(credentials=credentials)


def extract_text_from_image(image_path: Path) -> str:
    """Extract text from image (using Google Cloud Vision API).
    
    Args:
        image_path: Image file path
        
    Returns:
        Extracted text
    """
    client = get_google_vision_client()
    
    # Read image
    with open(image_path, 'rb') as image_file:
        content = image_file.read()
    
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    
    if response.error.message:
        raise Exception(f"Google Vision API error: {response.error.message}")
    
    if response.text_annotations:
        return response.text_annotations[0].description
    
    return ""


def extract_text_with_boxes(image_path: Path) -> list[dict]:
    """Extract text and location information from image (using Google Cloud Vision API).
    
    Args:
        image_path: Image file path
        
    Returns:
        List of dictionaries containing text and location information
    """
    client = get_google_vision_client()
    
    # Read image
    with open(image_path, 'rb') as image_file:
        content = image_file.read()
    
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    
    if response.error.message:
        raise Exception(f"Google Vision API error: {response.error.message}")
    
    results = []
    
    if response.text_annotations:
        # First one is full text, rest are individual words/text regions
        for annotation in response.text_annotations[1:]:
            vertices = annotation.bounding_poly.vertices
            
            if len(vertices) >= 3:
                # Extract bounding box coordinates
                x_coords = [v.x for v in vertices]
                y_coords = [v.y for v in vertices]
                
                results.append({
                    'text': annotation.description,
                    'left': min(x_coords),
                    'top': min(y_coords),
                    'width': max(x_coords) - min(x_coords),
                    'height': max(y_coords) - min(y_coords),
                    'conf': getattr(annotation, 'confidence', 1.0) * 100
                })
    
    return results
