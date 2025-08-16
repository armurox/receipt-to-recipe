# Receipt → Recipe (Django + React)

Upload receipts, OCR ingredients, and fetch recipes via Spoonacular.

## Quickstart

### 1) Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # or your preferred venv
pip install -r requirements.txt
cp .env.example .env  # add your SPOONACULAR_API_KEY
python manage.py migrate
python manage.py runserver
```

### 2) Frontend
```bash
cd frontend
npm i
npm run dev
```

- Frontend expects the backend at `http://127.0.0.1:8000/api`. If different, set `VITE_API_BASE` in a `.env` file in `frontend/`.
- Upload a clear receipt image; the OCR is naive by default but easy to upgrade.
- Select ingredients and click *Find recipes*.

## Notes
- OCR uses `pytesseract`. Install Tesseract locally and set `TESSERACT_CMD` in `backend/.env` if needed.
- Recipe results are cached per exact ingredient set in the `RecipeCache` table.
- This is a starter you can extend with auth, better NLP normalization, or async jobs (Celery).
