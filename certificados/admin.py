from django.contrib import admin
from .models import Certificado


@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'curso', 'codigo_verificacion', 'fecha_emision')
    list_filter = ('fecha_emision',)
    search_fields = ('usuario__username', 'usuario__first_name', 'curso__titulo', 'codigo_verificacion')
    readonly_fields = ('codigo_verificacion', 'fecha_emision')