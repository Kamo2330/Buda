from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from menu.models import Club, Table, Product


class Order(models.Model):
    """Customer order from a specific table"""
    STATUS_CHOICES = [
        ('received', 'Received'),
        ('in_progress', 'In Progress'),
        ('ready', 'Ready'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid_at_table', 'Paid at Table'),
        ('paid_online', 'Paid Online'),
        ('failed', 'Payment Failed'),
    ]

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='orders')
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, blank=True)  # cash, card, snapscan, etc.
    
    # Customer info (optional)
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    
    # Order totals
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    staff_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number} - Table {self.table.number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number: club_slug + timestamp
            import time
            timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
            self.order_number = f"{self.club.slug.upper()}{timestamp}"
        super().save(*args, **kwargs)

    def calculate_totals(self):
        """Calculate order totals from order items"""
        self.subtotal = sum(item.total_price for item in self.items.all())
        # For now, no tax calculation - can be added later
        self.tax_amount = Decimal('0.00')
        self.total_amount = self.subtotal + self.tax_amount
        self.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])


class OrderItem(models.Model):
    """Individual items in an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Special instructions for this item
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['order', 'product']

    def __str__(self):
        return f"{self.product.name} x{self.quantity} - {self.order.order_number}"

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        
        # Update order totals when item is saved
        self.order.calculate_totals()