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

def article_to_dict(article):
    return {'id': article.id, 'name': article.name, 'description': article.description}

def tag_to_dict(tag):
    return {'id': tag.id, 'name': tag.name}

def expense_to_dict(expense):
    tags = Tag.objects.filter(expense_tags__expense=expense)
    return {
        'id': expense.id,
        'amount': float(expense.amount),
        'description': expense.description,
        'expense_date': str(expense.expense_date),
        'article': {'id': expense.article.id, 'name': expense.article.name},
        'tags': [tag_to_dict(tag) for tag in tags],
    }

def period_range(period, reference_date=None):
    reference_date = reference_date or date.today()
    if period == 'today':
        return reference_date, reference_date
    if period == 'week':
        return reference_date - timedelta(days=6), reference_date
    if period == 'month':
        return reference_date - timedelta(days=29), reference_date
    if period == 'year':
        return reference_date - timedelta(days=364), reference_date
    return None, None

def get_reference_date(request):
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
        data = [article_to_dict(article) for article in ExpenseArticle.objects.all()]
        return JsonResponse({'count': len(data), 'data': data})

    def post(self, request):
        form = ExpenseArticleForm(loads(request.body))
        if form.is_valid():
            category = form.save(commit=False)
            category.user = get_current_user(request)
            if ExpenseArticle.objects.filter(user=category.user, name=category.name).exists():
                return JsonResponse({'error': 'Имя уже занято'}, status=400)
            category.save()
            return JsonResponse(article_to_dict(category), status=201)
        return JsonResponse({'errors': form.errors}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class CategoryDetailView(View):
    def get(self, request, category_id):
        category = get_object_or_404(ExpenseArticle, id=category_id)
        return JsonResponse(article_to_dict(category))

    def put(self, request, category_id):
        category = get_object_or_404(ExpenseArticle, id=category_id)
        form = ExpenseArticleForm(loads(request.body), instance=category)
        if form.is_valid():
            form.save()
            return JsonResponse(article_to_dict(category))
        return JsonResponse({'errors': form.errors}, status=400)

    def patch(self, request, category_id):
        category = get_object_or_404(ExpenseArticle, id=category_id)
        data = loads(request.body)
        if 'name' in data:
            category.name = data['name']
        if 'description' in data:
            category.description = data['description']
        category.save()
        return JsonResponse(article_to_dict(category))

    def delete(self, request, category_id):
        category = get_object_or_404(ExpenseArticle, id=category_id)
        category.delete()
        return JsonResponse({'status': 'ok'})

class CategoryExpensesView(View):
    def get(self, request, category_id):
        category = get_object_or_404(ExpenseArticle, id=category_id)
        expenses = Expense.objects.filter(article=category)
        return JsonResponse({
            'category': article_to_dict(category),
            'count': expenses.count(),
            'total': float(sum(expense.amount for expense in expenses)),
            'data': [expense_to_dict(expense) for expense in expenses],
        })

class CategoryStatsView(View):
    def get(self, request, category_id):
        category = get_object_or_404(ExpenseArticle, id=category_id)
        expenses = Expense.objects.filter(article=category)
        return JsonResponse({
            'category': article_to_dict(category),
            'count': expenses.count(),
            'total': float(sum(expense.amount for expense in expenses)),
        })

@method_decorator(csrf_exempt, name='dispatch')
class ExpenseListView(View):
    def get(self, request):
        data = [expense_to_dict(expense) for expense in Expense.objects.all()]
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
            return JsonResponse(expense_to_dict(expense), status=201)
        return JsonResponse({'errors': form.errors}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class ExpenseDetailView(View):
    def get(self, request, expense_id):
        expense = get_object_or_404(Expense, id=expense_id)
        return JsonResponse(expense_to_dict(expense))

    def put(self, request, expense_id):
        expense = get_object_or_404(Expense, id=expense_id)
        new_data = loads(request.body)
        tag_ids = new_data.pop('tag_ids', None)
        form = ExpenseForm(new_data, instance=expense)
        if form.is_valid():
            form.save()
            if tag_ids is not None:
                ExpenseTag.objects.filter(expense=expense).delete()
                for tag_id in tag_ids:
                    ExpenseTag.objects.create(expense=expense, tag_id=tag_id)
            return JsonResponse(expense_to_dict(expense))
        return JsonResponse({'errors': form.errors}, status=400)

    def patch(self, request, expense_id):
        expense = get_object_or_404(Expense, id=expense_id)
        data = loads(request.body)
        tag_ids = data.pop('tag_ids', None)
        if 'article' in data:
            expense.article_id = data['article']
        if 'amount' in data:
            expense.amount = data['amount']
        if 'description' in data:
            expense.description = data['description']
        if 'expense_date' in data:
            parsed = parse_date(data['expense_date'])
            if parsed:
                expense.expense_date = parsed
        expense.save()
        if tag_ids is not None:
            ExpenseTag.objects.filter(expense=expense).delete()
            for tag_id in tag_ids:
                ExpenseTag.objects.create(expense=expense, tag_id=tag_id)
        return JsonResponse(expense_to_dict(expense))

    def delete(self, request, expense_id):
        expense = get_object_or_404(Expense, id=expense_id)
        expense.delete()
        return JsonResponse({'status': 'ok'})

@method_decorator(csrf_exempt, name='dispatch')
class TagListView(View):
    def get(self, request):
        data = [tag_to_dict(tag) for tag in Tag.objects.all()]
        return JsonResponse({'count': len(data), 'data': data})

    def post(self, request):
        form = TagForm(loads(request.body))
        if form.is_valid():
            tag = form.save(commit=False)
            tag.user = get_current_user(request)
            if Tag.objects.filter(user=tag.user, name=tag.name).exists():
                return JsonResponse({'error': 'Имя уже занято'}, status=400)
            tag.save()
            return JsonResponse(tag_to_dict(tag), status=201)
        return JsonResponse({'errors': form.errors}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class TagDetailView(View):
    def get(self, request, tag_id):
        tag = get_object_or_404(Tag, id=tag_id)
        return JsonResponse(tag_to_dict(tag))

    def put(self, request, tag_id):
        tag = get_object_or_404(Tag, id=tag_id)
        form = TagForm(loads(request.body), instance=tag)
        if form.is_valid():
            form.save()
            return JsonResponse(tag_to_dict(tag))
        return JsonResponse({'errors': form.errors}, status=400)

    def patch(self, request, tag_id):
        tag = get_object_or_404(Tag, id=tag_id)
        data = loads(request.body)
        if 'name' in data:
            tag.name = data['name']
        tag.save()
        return JsonResponse(tag_to_dict(tag))

    def delete(self, request, tag_id):
        tag = get_object_or_404(Tag, id=tag_id)
        tag.delete()
        return JsonResponse({'status': 'ok'})

class TagStatsView(View):
    def get(self, request, tag_id):
        tag = get_object_or_404(Tag, id=tag_id)
        expense_ids = ExpenseTag.objects.filter(tag=tag).values_list('expense_id', flat=True)
        expenses = Expense.objects.filter(id__in=expense_ids)
        return JsonResponse({
            'tag': tag_to_dict(tag),
            'count': expenses.count(),
            'total': float(sum(expense.amount for expense in expenses)),
        })

class StatsPeriodView(View):
    def get(self, request, period):
        date_from, date_to = period_range(period, get_reference_date(request))
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
            date_from, date_to = period_range('month', get_reference_date(request))
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