import logging
from typing import Tuple, List, Callable
from django.conf import settings

from .ocr_types import OCRService, get_ocr_service_from_string

logger = logging.getLogger(__name__)

def get_ocr_service(model: str = None) -> Callable[[str], Tuple[str, List[str]]]:
    if model == 'tesseract':
        return _get_tesseract_service()
    elif model and model != 'tesseract':
        return _get_openrouter_service(model)
    else:
        service_setting = getattr(settings, 'OCR_SERVICE', 'tesseract')
        ocr_service = get_ocr_service_from_string(service_setting)
        logger.info("Using OCR service: %s", ocr_service.value)
        
        if ocr_service == OCRService.OPENROUTER:
            return _get_openrouter_service()
        else:
            return _get_tesseract_service()

def _get_openrouter_service(model: str = None) -> Callable[[str], Tuple[str, List[str]]]:
    try:
        from .openrouter_ocr import extract_ingredients_from_image as openrouter_extract
        
        api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
        if not api_key:
            logger.warning("OPENROUTER_API_KEY not configured, falling back to Tesseract")
            return _get_tesseract_service()
        
        def openrouter_with_fallback(path: str) -> Tuple[str, List[str]]:
            try:
                text, ingredients = openrouter_extract(path, model)
                
                if not text and not ingredients:
                    logger.warning("OpenRouter returned empty results, falling back to Tesseract")
                    return _get_tesseract_service()(path)
                
                return text, ingredients
                
            except Exception as e:
                logger.error("OpenRouter OCR failed, falling back to Tesseract: %s", e)
                return _get_tesseract_service()(path)
        
        return openrouter_with_fallback
        
    except ImportError as e:
        logger.error("Failed to import OpenRouter OCR service, falling back to Tesseract: %s", e)
        return _get_tesseract_service()

def _get_tesseract_service() -> Callable[[str], Tuple[str, List[str]]]:
    try:
        from .ocr import extract_ingredients_from_image as tesseract_extract
        return tesseract_extract
    except ImportError as e:
        logger.error("Failed to import Tesseract OCR service: %s", e)
        def dummy_ocr(path: str) -> Tuple[str, List[str]]:
            logger.error("No OCR service available")
            return "", []
        return dummy_ocr

def extract_ingredients_from_image(path: str, model: str = None) -> Tuple[str, List[str]]:
    ocr_service = get_ocr_service(model)
    return ocr_service(path)