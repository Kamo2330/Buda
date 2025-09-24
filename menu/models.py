from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Club(models.Model):
    """Represents a club/bar venue"""
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    address = models.TextField()
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    logo = models.ImageField(upload_to='clubs/logos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Table(models.Model):
    """Represents a table/booth in a club"""
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='tables')
    number = models.CharField(max_length=10)
    qr_code = models.CharField(max_length=100, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['club', 'number']
        ordering = ['number']

    def __str__(self):
        return f"{self.club.name} - Table {self.number}"

    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.qr_code = f"{self.club.slug}_table_{self.number}"
        super().save(*args, **kwargs)


class Category(models.Model):
    """Product categories like Beers, Ciders, etc."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # For emoji or icon class
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    """Individual products like Castle Lager, Savannah Dry, etc."""
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    stock_quantity = models.PositiveIntegerField(default=0, null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category__display_order', 'display_order', 'name']

    def __str__(self):
        return f"{self.name} - {self.club.name}"

    @property
    def is_in_stock(self):
        if self.stock_quantity is None:
            return self.is_available
        return self.is_available and self.stock_quantity > 0