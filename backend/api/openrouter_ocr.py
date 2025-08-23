import base64
import json
import logging
from typing import List, Tuple, Optional
from PIL import Image
from openai import OpenAI
from django.conf import settings
from .image_processor import preprocess_image

logger = logging.getLogger(__name__)

INGREDIENT_EXTRACTION_PROMPT = """
Analyze this receipt image and extract ONLY food ingredients that could be used for cooking recipes.

Rules:
1. Extract only actual food ingredients (vegetables, fruits, meats, dairy, spices, grains, etc.)
2. Ignore non-food items (cleaning supplies, toiletries, paper products, etc.)  
3. Ignore store metadata (prices, dates, store names, addresses, tax info, etc.)
4. Return each ingredient as a simple, canonical name (e.g., "ground beef" not "AUX BEEF MINCE")
5. Use singular forms when possible (e.g., "tomato" not "tomatoes")
6. Use common cooking names (e.g., "bell pepper" not "capsicum")

Look for food items even if abbreviated or coded. For example:
- "YOG" or "YOGURT" → "yogurt"  
- "WTR" or "WATER" → "water"
- "MILK" or "MLK" → "milk"
- "CHKN" → "chicken"

Return your response as valid JSON in this exact format:
{
  "ingredients": ["ingredient1", "ingredient2", "ingredient3"],
  "raw_text": "all text you can see in the image"
}

If you cannot clearly identify any ingredients, return:
{
  "ingredients": [],
  "raw_text": "any text you can see"
}
"""

def _encode_image_to_base64(image_path: str) -> str:
    try:
        with Image.open(image_path) as img:
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            import io
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            
            return base64.b64encode(buffer.read()).decode('utf-8')
    except Exception as e:
        logger.error("Failed to encode image %s: %s", image_path, e)
        raise

def _parse_openrouter_response(response_text: str) -> Tuple[str, List[str]]:
    try:
        if not response_text:
            return "", []
        
        stripped_response = response_text.strip()
        if not stripped_response:
            return "", []
        
        json_content = stripped_response
        if stripped_response.startswith('```json'):
            lines = stripped_response.split('\n')
            json_lines = []
            in_json_block = False
            
            for line in lines:
                if line.strip() == '```json':
                    in_json_block = True
                    continue
                elif line.strip() == '```' and in_json_block:
                    break
                elif in_json_block:
                    json_lines.append(line)
            
            json_content = '\n'.join(json_lines).strip()
        
        data = json.loads(json_content)
        raw_text = data.get('raw_text', '')
        ingredients = [ing.strip().lower() for ing in data.get('ingredients', []) if ing.strip()]
        return raw_text, ingredients
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error("Failed to parse JSON response: %s", e)
        if response_text and isinstance(response_text, str):
            return response_text, []
        return "", []

def _call_openrouter_vision(image_path: str, model: str = None) -> str:
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=getattr(settings, 'OPENROUTER_API_KEY', '')
        )
        
        if not client.api_key:
            raise ValueError("OPENROUTER_API_KEY not configured")
        
        base64_image = _encode_image_to_base64(image_path)
        model = model or getattr(settings, 'OPENROUTER_MODEL', 'openai/gpt-4o')
        
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": INGREDIENT_EXTRACTION_PROMPT
                }, {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }]
            }],
            max_tokens=1000,
            temperature=0.1
        )
        
        return response.choices[0].message.content or ""
        
    except Exception as e:
        logger.error("OpenRouter API call failed: %s", e)
        raise

def extract_ingredients_from_image(path: str, model: str = None) -> Tuple[str, List[str]]:
    try:
        processed_path = preprocess_image(path)
        response_text = _call_openrouter_vision(processed_path, model)
        raw_text, ingredients = _parse_openrouter_response(response_text)
        return raw_text, ingredients
    except Exception as e:
        logger.error("OpenRouter OCR failed for %s: %s", path, e)
        return "", []