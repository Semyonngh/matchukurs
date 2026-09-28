from datetime import date, timedelta
from json import loads
from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils.dateparse import parse_date
from django.contrib.auth.models import User
from .models import ExpenseArticle, Tag, Expense, ExpenseTag
from .forms import ExpenseArticleForm, TagForm, ExpenseForm

def to_dict_article(article):
    return {'id': article.id, 'name': article.name, 'description': article.description}

def to_dict_tag(tag):
    return {'id': tag.id, 'name': tag.name}

def to_dict_expense(expense):
    tags = Tag.objects.filter(expense_tags__expense=expense)
    return {
        'id': expense.id,
        'amount': float(expense.amount),
        'description': expense.description,
        'expense_date': str(expense.expense_date),
        'article': {'id': expense.article.id, 'name': expense.article.name},
        'tags': [to_dict_tag(tag) for tag in tags],
    }

def period_range(period, ref_date=None):
    ref_date = ref_date or date.today()
    if period == 'today':
        return ref_date, ref_date
    if period == 'week':
        return ref_date - timedelta(days=6), ref_date
    if period == 'month':
        return ref_date - timedelta(days=29), ref_date
    if period == 'year':
        return ref_date - timedelta(days=364), ref_date
    return None, None

def get_ref_date(request):
    raw = request.GET.get('date')
    if raw:
        parsed = parse_date(raw)
        if parsed:
            return parsed
    return date.today()

def get_current_user(request):
    return request.user if request.user.is_authenticated else User.objects.first()

@method_decorator(csrf_exempt, name='dispatch')
class CategoryListView(View):
    def get(self, request):
        data = [to_dict_article(article) for article in ExpenseArticle.objects.all()]
        return JsonResponse({'count': len(data), 'data': data})

    def post(self, request):
        form = ExpenseArticleForm(loads(request.body))
        if form.is_valid():
            category = form.save(commit=False)
            category.user = get_current_user(request)
            if ExpenseArticle.objects.filter(user=category.user, name=category.name).exists():
                return JsonResponse({'error': 'Имя уже занято'}, status=400)
            category.save()
            return JsonResponse(to_dict_article(category), status=201)
        return JsonResponse({'errors': form.errors}, status=400)

class CategoryDetailView(View):
    def get(self, request, category_id):
        category = get_object_or_404(ExpenseArticle, id=category_id)
        return JsonResponse(to_dict_article(category))

class CategoryExpensesView(View):
    def get(self, request, category_id):
        category = get_object_or_404(ExpenseArticle, id=category_id)
        expenses = Expense.objects.filter(article=category)
        return JsonResponse({
            'category': to_dict_article(category),
            'count': expenses.count(),
            'total': float(sum(expense.amount for expense in expenses)),
            'data': [to_dict_expense(expense) for expense in expenses],
        })

class CategoryStatsView(View):
    def get(self, request, category_id):
        category = get_object_or_404(ExpenseArticle, id=category_id)
        expenses = Expense.objects.filter(article=category)
        return JsonResponse({
            'category': to_dict_article(category),
            'count': expenses.count(),
            'total': float(sum(expense.amount for expense in expenses)),
        })

@method_decorator(csrf_exempt, name='dispatch')
class ExpenseListView(View):
    def get(self, request):
        data = [to_dict_expense(expense) for expense in Expense.objects.all()]
        return JsonResponse({'count': len(data), 'data': data})

    def post(self, request):
        new_data = loads(request.body)
        tag_ids = new_data.pop('tag_ids', [])
        form = ExpenseForm(new_data)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = get_current_user(request)
            expense.save()
            for tag_id in tag_ids:
                ExpenseTag.objects.create(expense=expense, tag_id=tag_id)
            return JsonResponse(to_dict_expense(expense), status=201)
        return JsonResponse({'errors': form.errors}, status=400)

class ExpenseDetailView(View):
    def get(self, request, expense_id):
        expense = get_object_or_404(Expense, id=expense_id)
        return JsonResponse(to_dict_expense(expense))

@method_decorator(csrf_exempt, name='dispatch')
class TagListView(View):
    def get(self, request):
        data = [to_dict_tag(tag) for tag in Tag.objects.all()]
        return JsonResponse({'count': len(data), 'data': data})

    def post(self, request):
        form = TagForm(loads(request.body))
        if form.is_valid():
            tag = form.save(commit=False)
            tag.user = get_current_user(request)
            if Tag.objects.filter(user=tag.user, name=tag.name).exists():
                return JsonResponse({'error': 'Имя уже занято'}, status=400)
            tag.save()
            return JsonResponse(to_dict_tag(tag), status=201)
        return JsonResponse({'errors': form.errors}, status=400)

class TagDetailView(View):
    def get(self, request, tag_id):
        tag = get_object_or_404(Tag, id=tag_id)
        return JsonResponse(to_dict_tag(tag))

class TagStatsView(View):
    def get(self, request, tag_id):
        tag = get_object_or_404(Tag, id=tag_id)
        ids = ExpenseTag.objects.filter(tag=tag).values_list('expense_id', flat=True)
        expenses = Expense.objects.filter(id__in=ids)
        return JsonResponse({
            'tag': to_dict_tag(tag),
            'count': expenses.count(),
            'total': float(sum(expense.amount for expense in expenses)),
        })

class StatsAllView(View):
    def get(self, request):
        expenses = Expense.objects.all()
        return JsonResponse({
            'count': expenses.count(),
            'total': float(sum(expense.amount for expense in expenses)),
        })

class StatsPeriodView(View):
    def get(self, request, period):
        date_from, date_to = period_range(period, get_ref_date(request))
        expenses = Expense.objects.filter(expense_date__gte=date_from, expense_date__lte=date_to)
        return JsonResponse({
            'period': period,
            'from': str(date_from),
            'to': str(date_to),
            'count': expenses.count(),
            'total': float(sum(expense.amount for expense in expenses)),
        })

class StatsCustomPeriodView(View):
    def get(self, request):
        date_from = parse_date(request.GET.get('from', ''))
        date_to = parse_date(request.GET.get('to', ''))
        if not date_from or not date_to:
            return JsonResponse({'error': 'from и to обязательны'}, status=400)
        expenses = Expense.objects.filter(expense_date__gte=date_from, expense_date__lte=date_to)
        return JsonResponse({
            'period': 'custom',
            'from': str(date_from),
            'to': str(date_to),
            'count': expenses.count(),
            'total': float(sum(expense.amount for expense in expenses)),
        })

class StatsTodayView(View):
    def get(self, request):
        today = date.today()
        expenses = Expense.objects.filter(expense_date=today)
        return JsonResponse({
            'period': 'today',
            'date': str(today),
            'count': expenses.count(),
            'total': float(sum(expense.amount for expense in expenses)),
        })

class StatsByCategoryView(View):
    def get(self, request):
        date_from = parse_date(request.GET.get('from', ''))
        date_to = parse_date(request.GET.get('to', ''))
        if not date_from or not date_to:
            date_from, date_to = period_range('month', get_ref_date(request))

        expenses = Expense.objects.filter(expense_date__gte=date_from, expense_date__lte=date_to)
        data = []
        for category in ExpenseArticle.objects.all():
            category_expenses = expenses.filter(article=category)
            data.append({
                'category_id': category.id,
                'name': category.name,
                'count': category_expenses.count(),
                'total': float(sum(expense.amount for expense in category_expenses)),
            })
        return JsonResponse({
            'from': str(date_from),
            'to': str(date_to),
            'total': float(sum(expense.amount for expense in expenses)),
            'data': data,
        })