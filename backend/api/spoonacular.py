import logging
import os
import requests
from typing import List
from django.conf import settings

BASE = 'https://api.spoonacular.com'

def find_recipes_by_ingredients(ingredient_names: List[str], number: int = 10):
    api_key = settings.SPOONACULAR_API_KEY or os.getenv('SPOONACULAR_API_KEY', '')
    if not api_key:
        raise RuntimeError('Missing SPOONACULAR_API_KEY in environment')
    params = {
        'ingredients': ','.join(ingredient_names),
        'number': number,
        'ranking': 1,
        'ignorePantry': True,
        'apiKey': api_key,
    }
    r = requests.get(f'{BASE}/recipes/findByIngredients', params=params, timeout=20)
    r.raise_for_status()
    print('Response is', r.json())
    return r.json()
