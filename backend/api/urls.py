from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReceiptViewSet, IngredientViewSet, RecipeView, SettingsView

router = DefaultRouter()
router.register(r'receipts', ReceiptViewSet, basename='receipt')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')

urlpatterns = [
    path('', include(router.urls)),
    path('recipes/', RecipeView.as_view(), name='recipes-by-ingredients'),
    path('settings/', SettingsView.as_view(), name='settings'),
]
