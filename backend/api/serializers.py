from rest_framework import serializers
from .models import Ingredient, Receipt

class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name']

class ReceiptSerializer(serializers.ModelSerializer):
    ingredients = IngredientSerializer(many=True, read_only=True)
    class Meta:
        model = Receipt
        fields = ['id', 'image', 'ocr_text', 'created_at', 'ingredients']
        read_only_fields = ['ocr_text', 'created_at', 'ingredients']

class ReceiptUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = ['image']
