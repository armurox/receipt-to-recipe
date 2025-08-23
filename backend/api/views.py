import hashlib
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Ingredient, Receipt, RecipeCache
from .serializers import IngredientSerializer, ReceiptSerializer, ReceiptUploadSerializer
from .ocr_factory import extract_ingredients_from_image
from .spoonacular import find_recipes_by_ingredients
from django.conf import settings

class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all().order_by('name')
    serializer_class = IngredientSerializer

class ReceiptViewSet(viewsets.ModelViewSet):
    queryset = Receipt.objects.all().order_by('-created_at')
    serializer_class = ReceiptSerializer

    def get_serializer_class(self):
        if self.action in ['create']:
            return ReceiptUploadSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        receipt = serializer.save()
        
        model = request.data.get('model')
        text, names = extract_ingredients_from_image(receipt.image.path, model)
        receipt.ocr_text = text
        ing_objs = []
        for name in names:
            obj, _ = Ingredient.objects.get_or_create(name=name)
            ing_objs.append(obj)
        with transaction.atomic():
            receipt.save()
            receipt.ingredients.set(ing_objs)
        out = ReceiptSerializer(receipt, context={'request': request}).data
        return Response(out, status=status.HTTP_201_CREATED)

class RecipeView(APIView):
    def post(self, request):
        ids = request.data.get('ingredient_ids') or []
        try:
            number = int(request.data.get('number', 10))
        except Exception:
            number = 10
        if not ids:
            return Response({'detail': 'ingredient_ids required'}, status=400)
        names = list(Ingredient.objects.filter(id__in=ids).order_by('name').values_list('name', flat=True))
        if not names:
            return Response({'detail': 'No matching ingredients found'}, status=404)
        key = hashlib.sha256((','.join(names)).encode('utf-8')).hexdigest()
        cached = RecipeCache.objects.filter(ingredients_hash=key).first()
        if cached:
            return Response(cached.response_json)
        data = find_recipes_by_ingredients(names, number=number)
        RecipeCache.objects.create(ingredients_hash=key, response_json=data)
        return Response(data)

class SettingsView(APIView):
    def get(self, request):
        available_models = [
            {'id': 'openai/gpt-4o', 'name': 'GPT-4 Vision (Fast & Accurate)'},
            {'id': 'openai/gpt-4o-mini', 'name': 'GPT-4 Vision Mini (Fastest)'},
            {'id': 'anthropic/claude-3.5-sonnet', 'name': 'Claude 3.5 Sonnet (Most Accurate)'},
            {'id': 'anthropic/claude-3-haiku', 'name': 'Claude 3 Haiku (Fast)'},
            {'id': 'google/gemini-pro-vision', 'name': 'Gemini Pro Vision'},
            {'id': 'tesseract', 'name': 'Tesseract (Free, Local OCR)'}
        ]
        current_ocr_service = getattr(settings, 'OCR_SERVICE', 'openrouter')
        current_model = getattr(settings, 'OPENROUTER_MODEL', 'openai/gpt-4o')
        
        return Response({
            'available_models': available_models,
            'current_ocr_service': current_ocr_service,
            'current_model': current_model if current_ocr_service == 'openrouter' else 'tesseract'
        })
