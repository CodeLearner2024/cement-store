from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import Category, Product, ProductImage, Cart, CartItem, Order, OrderItem, Review


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'image_preview', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description')
        }),
        ('Image', {
            'fields': ('image', 'image_preview'),
            'classes': ('collapse', 'wide')
        }),
    )
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return "Aucune image"
    image_preview.short_description = 'Aperçu'


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'image_preview')
    readonly_fields = ('image_preview',)
    verbose_name = 'Image supplémentaire'
    verbose_name_plural = 'Images supplémentaires'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return "Aucune image"
    image_preview.short_description = 'Aperçu'


class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock', 'available', 'image_preview', 'created_at')
    list_filter = ('available', 'created_at', 'updated_at', 'category')
    list_editable = ('price', 'stock', 'available')
    search_fields = ('name', 'description', 'category__name')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        ('Prix et stock', {
            'fields': ('price', 'stock', 'available')
        }),
        ('Image principale', {
            'fields': ('image', 'image_preview'),
            'classes': ('collapse', 'wide')
        }),
    )
    readonly_fields = ('image_preview',)
    inlines = [ProductImageInline]
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return "Aucune image"
    image_preview.short_description = 'Aperçu'


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'updated_at', 'total_quantity', 'total_price')
    list_filter = ('created_at', 'updated_at')
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'first_name', 'last_name', 'email', 'status', 'paid', 'created_at', 'total_amount')
    list_filter = ('status', 'paid', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'id')
    inlines = [OrderItemInline]


class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'comment')


admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Review, ReviewAdmin)
