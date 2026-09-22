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

def to_dict_article(a):
    return {'id': a.id, 'name': a.name, 'description': a.description}

def to_dict_tag(t):
    return {'id': t.id, 'name': t.name}

def to_dict_expense(e):
    tags = Tag.objects.filter(expense_tags__expense=e)
    return {
        'id': e.id,
        'amount': float(e.amount),
        'description': e.description,
        'expense_date': str(e.expense_date),
        'article': {'id': e.article.id, 'name': e.article.name},
        'tags': [to_dict_tag(t) for t in tags],
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
        data = [to_dict_article(a) for a in ExpenseArticle.objects.all()]
        return JsonResponse({'count': len(data), 'data': data})

    def post(self, request):
        form = ExpenseArticleForm(loads(request.body))
        if form.is_valid():
            c = form.save(commit=False)
            c.user = get_current_user(request)
            if ExpenseArticle.objects.filter(user=c.user, name=c.name).exists():
                return JsonResponse({'error': 'Имя уже занято'}, status=400)
            c.save()
            return JsonResponse(to_dict_article(c), status=201)
        return JsonResponse({'errors': form.errors}, status=400)

class CategoryDetailView(View):
    def get(self, request, category_id):
        c = get_object_or_404(ExpenseArticle, id=category_id)
        return JsonResponse(to_dict_article(c))

class CategoryExpensesView(View):
    def get(self, request, category_id):
        c = get_object_or_404(ExpenseArticle, id=category_id)
        expenses = Expense.objects.filter(article=c)
        return JsonResponse({
            'category': to_dict_article(c),
            'count': expenses.count(),
            'total': float(sum(e.amount for e in expenses)),
            'data': [to_dict_expense(e) for e in expenses],
        })

class CategoryStatsView(View):
    def get(self, request, category_id):
        c = get_object_or_404(ExpenseArticle, id=category_id)
        expenses = Expense.objects.filter(article=c)
        return JsonResponse({
            'category': to_dict_article(c),
            'count': expenses.count(),
            'total': float(sum(e.amount for e in expenses)),
        })

@method_decorator(csrf_exempt, name='dispatch')
class ExpenseListView(View):
    def get(self, request):
        data = [to_dict_expense(e) for e in Expense.objects.all()]
        return JsonResponse({'count': len(data), 'data': data})

    def post(self, request):
        new_data = loads(request.body)
        tag_ids = new_data.pop('tag_ids', [])
        form = ExpenseForm(new_data)
        if form.is_valid():
            e = form.save(commit=False)
            e.user = get_current_user(request)
            e.save()
            for tid in tag_ids:
                ExpenseTag.objects.create(expense=e, tag_id=tid)
            return JsonResponse(to_dict_expense(e), status=201)
        return JsonResponse({'errors': form.errors}, status=400)

class ExpenseDetailView(View):
    def get(self, request, expense_id):
        e = get_object_or_404(Expense, id=expense_id)
        return JsonResponse(to_dict_expense(e))

@method_decorator(csrf_exempt, name='dispatch')
class TagListView(View):
    def get(self, request):
        data = [to_dict_tag(t) for t in Tag.objects.all()]
        return JsonResponse({'count': len(data), 'data': data})

    def post(self, request):
        form = TagForm(loads(request.body))
        if form.is_valid():
            t = form.save(commit=False)
            t.user = get_current_user(request)
            if Tag.objects.filter(user=t.user, name=t.name).exists():
                return JsonResponse({'error': 'Имя уже занято'}, status=400)
            t.save()
            return JsonResponse(to_dict_tag(t), status=201)
        return JsonResponse({'errors': form.errors}, status=400)

class TagDetailView(View):
    def get(self, request, tag_id):
        t = get_object_or_404(Tag, id=tag_id)
        return JsonResponse(to_dict_tag(t))

class TagStatsView(View):
    def get(self, request, tag_id):
        t = get_object_or_404(Tag, id=tag_id)
        ids = ExpenseTag.objects.filter(tag=t).values_list('expense_id', flat=True)
        expenses = Expense.objects.filter(id__in=ids)
        return JsonResponse({
            'tag': to_dict_tag(t),
            'count': expenses.count(),
            'total': float(sum(e.amount for e in expenses)),
        })

class StatsAllView(View):
    def get(self, request):
        expenses = Expense.objects.all()
        return JsonResponse({
            'count': expenses.count(),
            'total': float(sum(e.amount for e in expenses)),
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
            'total': float(sum(e.amount for e in expenses)),
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
            'total': float(sum(e.amount for e in expenses)),
        })

class StatsTodayView(View):
    def get(self, request):
        today = date.today()
        expenses = Expense.objects.filter(expense_date=today)
        return JsonResponse({
            'period': 'today',
            'date': str(today),
            'count': expenses.count(),
            'total': float(sum(e.amount for e in expenses)),
        })

class StatsByCategoryView(View):
    def get(self, request):
        date_from = parse_date(request.GET.get('from', ''))
        date_to = parse_date(request.GET.get('to', ''))
        if not date_from or not date_to:
            date_from, date_to = period_range('month', get_ref_date(request))

        expenses = Expense.objects.filter(expense_date__gte=date_from, expense_date__lte=date_to)
        data = []
        for c in ExpenseArticle.objects.all():
            cat_expenses = expenses.filter(article=c)
            data.append({
                'category_id': c.id,
                'name': c.name,
                'count': cat_expenses.count(),
                'total': float(sum(e.amount for e in cat_expenses)),
            })
        return JsonResponse({
            'from': str(date_from),
            'to': str(date_to),
            'total': float(sum(e.amount for e in expenses)),
            'data': data,
        })