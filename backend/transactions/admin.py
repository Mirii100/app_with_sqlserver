from django.contrib import admin
from .models import Transaction, SavingsGoal, GoalTransaction, Budget, UserLoanLimit

admin.site.register(Transaction)
admin.site.register(SavingsGoal)
admin.site.register(GoalTransaction)
admin.site.register(Budget)
admin.site.register(UserLoanLimit)
