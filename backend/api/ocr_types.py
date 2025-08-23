from enum import Enum
from typing import Optional

class OCRService(Enum):
    TESSERACT = "tesseract"
    OPENROUTER = "openrouter"

def get_ocr_service_from_string(service_name: Optional[str]) -> OCRService:
    if not service_name:
        return OCRService.TESSERACT
    
    service_name = service_name.lower().strip()
    
    if service_name == "openrouter":
        return OCRService.OPENROUTER
    elif service_name == "tesseract":
        return OCRService.TESSERACT
    else:
        return OCRService.TESSERACT

def is_valid_ocr_service(service_name: Optional[str]) -> bool:
    if not service_name:
        return True
    
    try:
        get_ocr_service_from_string(service_name)
        return True
    except Exception:
        return False