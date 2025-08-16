from django.db import models

class Ingredient(models.Model):
    name = models.CharField(max_length=255, unique=True)
    def __str__(self):
        return self.name

class Receipt(models.Model):
    image = models.ImageField(upload_to='receipts/')
    ocr_text = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    ingredients = models.ManyToManyField(Ingredient, related_name='receipts', blank=True)
    def __str__(self):
        return f"Receipt {self.pk}"

class RecipeCache(models.Model):
    ingredients_hash = models.CharField(max_length=64, db_index=True, unique=True)
    response_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.ingredients_hash[:8]
