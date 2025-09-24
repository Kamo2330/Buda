from django.db import models
from django.contrib.auth.models import User
from menu.models import Club


class StaffMember(models.Model):
    """Staff members who can access the staff dashboard"""
    ROLE_CHOICES = [
        ('waiter', 'Waiter'),
        ('bartender', 'Bartender'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='staff')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    employee_id = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['club', 'employee_id']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.club.name}"


class SalesReport(models.Model):
    """Daily sales reports for clubs"""
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='sales_reports')
    date = models.DateField()
    total_orders = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_items_sold = models.PositiveIntegerField(default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    peak_hour = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['club', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.club.name} - {self.date}"


class ProductSales(models.Model):
    """Product sales data for reporting"""
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='product_sales')
    product = models.ForeignKey('menu.Product', on_delete=models.CASCADE)
    date = models.DateField()
    quantity_sold = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['club', 'product', 'date']
        ordering = ['-date', '-revenue']

    def __str__(self):
        return f"{self.product.name} - {self.date}"