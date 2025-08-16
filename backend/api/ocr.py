# backend/api/ocr.py
import re
import logging
from typing import List, Tuple, Optional
from PIL import Image, ImageOps, ImageFilter
import pytesseract
from django.conf import settings
from difflib import get_close_matches

logger = logging.getLogger(__name__)

if getattr(settings, 'TESSERACT_CMD', None):
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

STOPWORDS = {
    'subtotal','total','tax','vat','change','cash','cashier','operator','clerk','till',
    'merchant','store','branch','receipt','invoice','order','sale','refund','qty','item',
    'card','visa','mastercard','debit','credit','auth','approval','terminal','ref','pos',
    'date','time','no','#','phone','tel','fax','www','com','net','org','po','box',
    'dubai','uae','street','st','road','rd','avenue','ave','blvd','mall','floor'
}
UNITY = {'kg','g','mg','l','ml','oz','lb','lbs','doz','pkt','pc','pcs','each','ea'}

COMMON_INGREDIENTS = {
    'apple','banana','orange','lemon','lime','tomato','potato','onion','garlic','ginger',
    'carrot','broccoli','spinach','lettuce','cucumber','mushroom','pepper','chili',
    'chicken','beef','pork','fish','salmon','tuna','egg','eggs','milk','butter','yogurt',
    'cheese','cream','flour','sugar','salt','pepper','olive oil','vegetable oil','canola oil',
    'rice','pasta','noodles','bread','oats','honey','vinegar','soy sauce','baking powder',
    'baking soda','cocoa powder','cornstarch','yeast','vanilla','cinnamon','paprika','cumin',
    'turmeric','basil','parsley','cilantro','thyme','rosemary','oregano','chickpeas','beans',
    'lentils','tomato paste','tomato sauce','peas','corn','bell pepper','red onion'
}
MULTI_WORD = {i for i in COMMON_INGREDIENTS if ' ' in i}

META_PATTERNS = [
    re.compile(r'\b(trn|tax|vat|invoice|order|cashier|operator|clerk|terminal|auth|approval)\b', re.I),
    re.compile(r'(www\.|\.com|\.net|\.org|@)'),
    re.compile(r'\b(tel|phone|fax)\b', re.I),
    re.compile(r'\b(st|rd|ave|blvd|street|road|avenue|mall|floor|po box)\b', re.I),
]

def _is_mostly_digits_or_noise(s: str) -> bool:
    letters = sum(c.isalpha() for c in s)
    digits  = sum(c.isdigit() for c in s)
    return digits > letters or letters == 0

def _looks_like_metadata(s: str) -> bool:
    if any(sw in s for sw in STOPWORDS):
        return True
    return any(p.search(s) for p in META_PATTERNS)

def _basic_singular(word: str) -> str:
    if len(word) > 4 and word.endswith('ies'):
        return word[:-3] + 'y'
    if len(word) > 4 and word.endswith('oes'):
        return word[:-2]
    if len(word) > 3 and word.endswith('s'):
        return word[:-1]
    return word

def _normalize_tokens(tokens: List[str]) -> List[str]:
    out = []
    for t in tokens:
        t = t.strip().lower()
        if not t or t in UNITY:
            continue
        out.append(_basic_singular(t))
    return out

def _canonicalize(line_tokens: List[str]) -> Optional[str]:
    if not line_tokens:
        return None

    joined = ' '.join(line_tokens)

    for phrase in MULTI_WORD:
        if joined == phrase:
            return phrase

    if 2 <= len(line_tokens) <= 3:
        matches = get_close_matches(joined, list(MULTI_WORD), n=1, cutoff=0.86)
        if matches:
            return matches[0]

    if len(line_tokens) == 1 and line_tokens[0] in COMMON_INGREDIENTS:
        return line_tokens[0]

    if len(line_tokens) == 1:
        matches = get_close_matches(line_tokens[0], list(COMMON_INGREDIENTS), n=1, cutoff=0.86)
        if matches:
            return matches[0]

    if line_tokens[0] in COMMON_INGREDIENTS:
        return line_tokens[0]

    return None

def _clean_line(raw: str) -> Optional[str]:
    raw = re.sub(r'(\s|\.|,)*\d+[.,]\d{2}\s*$', ' ', raw)
    line = re.sub(r'[^A-Za-z\s]', ' ', raw).lower()
    line = re.sub(r'\s{2,}', ' ', line).strip()

    if not line or _is_mostly_digits_or_noise(line) or _looks_like_metadata(line):
        return None
    if len(line.split()) > 5:
        return None

    tokens = _normalize_tokens(line.split())
    if not tokens:
        return None
    if tokens[0] in STOPWORDS:
        return None

    return _canonicalize(tokens)

def _preprocess_image(img: Image.Image) -> Image.Image:
    try:
        img = ImageOps.exif_transpose(img)  # fix orientation if EXIF present
        img = img.convert('L')
        img = ImageOps.autocontrast(img)
        img = img.filter(ImageFilter.SHARPEN)
        w, h = img.size
        if min(w, h) < 900:
            img = img.resize((int(w * 1.5), int(h * 1.5)))
        return img
    except Exception as e:
        logger.warning("OCR preprocessing failed; falling back to raw image: %s", e)
        return img  # fall back to original

def _tesseract_lang() -> Optional[str]:
    try:
        langs = set(pytesseract.get_languages(config=''))
        return 'eng' if 'eng' in langs else None
    except Exception as e:
        logger.info("Could not query tesseract languages: %s", e)
        return None

def _run_ocr(img: Image.Image) -> str:
    lang = _tesseract_lang()
    cfg = "--oem 1 --psm 6 -c preserve_interword_spaces=1"
    try:
        return pytesseract.image_to_string(img, config=cfg, lang=lang) if lang else \
               pytesseract.image_to_string(img, config=cfg)
    except Exception as e:
        logger.warning("OCR with config failed (%s). Retrying with defaults.", e)
        # retry with no config
        try:
            return pytesseract.image_to_string(img, lang=lang) if lang else \
                   pytesseract.image_to_string(img)
        except Exception as e2:
            logger.error("OCR completely failed: %s", e2)
            # last resort empty text
            return ""

def extract_ingredients_from_image(path: str) -> Tuple[str, List[str]]:
    """
    Defensive pipeline: preprocess -> OCR (with fallback) -> filter/normalize
    If anything breaks, we return best-effort text and fall back to no-op filtering.
    """
    try:
        img = Image.open(path)
    except Exception as e:
        logger.error("Failed to open image %s: %s", path, e)
        return "", []

    img = _preprocess_image(img)
    text = _run_ocr(img)

    found = set()
    for raw in text.splitlines():
        raw = (raw or '').strip()
        if not raw:
            continue
        try:
            canon = _clean_line(raw)
        except Exception as e:
            # never crash on a bad line; just skip it
            logger.debug("Line clean error on '%s': %s", raw, e)
            canon = None
        if canon:
            found.add(canon)

    # Fallback behavior: if *nothing* survived filters, degrade gracefully and return
    # the old simple candidates (so uploads never 500)
    if not found:
        try:
            fallback_text = pytesseract.image_to_string(img)
            candidates = []
            for raw in fallback_text.splitlines():
                line = re.sub(r'[^A-Za-z\\s]', ' ', raw).strip().lower()
                line = re.sub(r'\\s{2,}', ' ', line)
                if not line or any(sw in line for sw in STOPWORDS):
                    continue
                if 1 <= len(line.split()) <= 4:
                    candidates.append(line)
            return fallback_text, sorted(set(candidates))
        except Exception as e:
            logger.error("Fallback OCR failed: %s", e)

    return text, sorted(found)
