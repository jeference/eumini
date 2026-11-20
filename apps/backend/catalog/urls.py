from django.urls import path

from catalog import views

urlpatterns = [
    path("catalog/products/", views.ProductListView.as_view(), name="catalog-products"),
]
