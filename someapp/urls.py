from django.urls import path
from . import views

urlpatterns = [
    path('categories', views.CategoryListView.as_view()),
    path('categories/<int:category_id>', views.CategoryDetailView.as_view()),
    path('categories/<int:category_id>/expenses', views.CategoryExpensesView.as_view()),
    path('categories/<int:category_id>/stats', views.CategoryStatsView.as_view()),
    path('expenses', views.ExpenseListView.as_view()),
    path('expenses/<int:expense_id>', views.ExpenseDetailView.as_view()),
    path('tags', views.TagListView.as_view()),
    path('tags/<int:tag_id>', views.TagDetailView.as_view()),
    path('tags/<int:tag_id>/stats', views.TagStatsView.as_view()),
    path('stats/week', views.StatsPeriodView.as_view(), {'period': 'week'}),
    path('stats/month', views.StatsPeriodView.as_view(), {'period': 'month'}),
    path('stats/year', views.StatsPeriodView.as_view(), {'period': 'year'}),
    path('stats/period', views.StatsCustomPeriodView.as_view()),
    path('stats/today', views.StatsTodayView.as_view()),
    path('stats/by-category', views.StatsByCategoryView.as_view()),
]