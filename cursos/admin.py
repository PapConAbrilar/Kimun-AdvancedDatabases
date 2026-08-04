from django.contrib import admin
from .models import Curso, Material, InscripcionCurso, Clase, ClaseCompletado, Categoria
from .forms import ClaseForm


class MaterialInline(admin.TabularInline):
    model = Material
    extra = 1
    fields = ('titulo', 'tipo', 'archivo', 'url')
    verbose_name_plural = 'Materiales'


class ClaseInline(admin.TabularInline):
    model = Clase
    extra = 1
    fields = ('titulo', 'orden', 'contenido')
    ordering = ('orden',)
    verbose_name_plural = 'Clases'
    form = ClaseForm


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'docente_creador', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'fecha_creacion')
    search_fields = ('titulo', 'descripcion')
    inlines = [MaterialInline, ClaseInline]
    fieldsets = (
        ('Información del Curso', {
            'fields': ('titulo', 'descripcion', 'docente_creador', 'estado')
        }),
    )


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'color')
    search_fields = ('nombre',)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'curso', 'tipo')
    list_filter = ('tipo',)
    search_fields = ('titulo', 'curso__titulo')


@admin.register(InscripcionCurso)
class InscripcionCursoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'curso', 'estado', 'fecha_asignacion')
    list_filter = ('estado', 'fecha_asignacion')
    search_fields = ('usuario__username', 'usuario__first_name', 'curso__titulo')


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'curso', 'orden', 'fecha_creacion')
    list_filter = ('curso',)
    search_fields = ('titulo', 'curso__titulo')
    ordering = ('curso', 'orden')
    form = ClaseForm
    readonly_fields = ('fecha_creacion',)
    add_fieldsets = (
        (None, {'fields': ('curso', 'titulo', 'contenido', 'orden')}),
    )
    fieldsets = (
        (None, {'fields': ('titulo', 'contenido', 'orden')}),
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)


@admin.register(ClaseCompletado)
class ClaseCompletadoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'clase', 'fecha_completado')
    list_filter = ('fecha_completado',)
    search_fields = ('usuario__username', 'clase__titulo')
