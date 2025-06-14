from rest_framework import viewsets, permissions
from .models import Category, Transaction, Budget
from .serializers import CategorySerializer, TransactionSerializer, BudgetSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Sum
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['type', 'name']
    ordering_fields = ['name']
    search_fields = ['name']

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = {
    'category': ['exact'],
    'amount': ['exact', 'gte', 'lte'],
    'date': ['exact', 'gte', 'lte'],
    'created_at': ['exact', 'gte', 'lte']
    }
    ordering_fields = ['amount', 'date', 'created_at']
    search_fields = ['description']

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
    'month': ['exact', 'gte', 'lte'],
    'amount': ['exact', 'gte', 'lte']
    }
    ordering_fields = ['month', 'amount']

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)



from datetime import datetime

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_summary(request):
    user = request.user
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    filters = {'user': user}
    if start_date:
        filters['date__gte'] = start_date
    if end_date:
        filters['date__lte'] = end_date

    income_total = Transaction.objects.filter(
        **filters,
        category__type='income'
    ).aggregate(total=Sum('amount'))['total'] or 0

    expense_total = Transaction.objects.filter(
        **filters,
        category__type='expense'
    ).aggregate(total=Sum('amount'))['total'] or 0

    balance = income_total - expense_total

    # 👇 Extract month part for exact budget lookup
    budget = None
    if start_date:
        try:
            month_obj = datetime.strptime(start_date, "%Y-%m-%d")
            month_start = month_obj.replace(day=1)
            budget = Budget.objects.filter(user=user, month=month_start).first()
        except:
            pass

    recent_txns = Transaction.objects.filter(user=user).select_related("category").order_by("-created_at")[:5]
    recent_txns_data = TransactionSerializer(recent_txns, many=True).data

    return Response({
        'total_income': income_total,
        'total_expense': expense_total,
        'balance': balance,
        'filtered_from': start_date,
        'filtered_to': end_date,
        'budget': BudgetSerializer(budget).data if budget else None,
        'recent_transactions': recent_txns_data
    })
