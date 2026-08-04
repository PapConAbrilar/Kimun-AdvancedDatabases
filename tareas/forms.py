from django import forms
from django.utils import timezone

from .models import Tarea, EntregaTarea


class TareaForm(forms.ModelForm):
    class Meta:
        model = Tarea
        fields = ['titulo', 'descripcion', 'fecha_limite', 'puntaje_maximo']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl',
                'placeholder': 'Título de la tarea'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl',
                'rows': 4,
                'placeholder': 'Descripción opcional'
            }),
            'fecha_limite': forms.DateTimeInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'puntaje_maximo': forms.NumberInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl',
                'min': 1
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_limite:
            self.initial['fecha_limite'] = self.instance.fecha_limite.strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        cleaned_data = super().clean()
        fecha_limite = cleaned_data.get('fecha_limite')

        if fecha_limite and not self.instance.pk and fecha_limite < timezone.now():
            raise forms.ValidationError('La fecha límite no puede estar en el pasado.')

        return cleaned_data


class EntregaTareaForm(forms.ModelForm):
    class Meta:
        model = EntregaTarea
        fields = ['archivo', 'comentario']
        widgets = {
            'archivo': forms.ClearableFileInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl',
            }),
            'comentario': forms.Textarea(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl',
                'rows': 4,
                'placeholder': 'Comentario opcional'
            }),
        }


class CalificacionForm(forms.ModelForm):
    class Meta:
        model = EntregaTarea
        fields = ['puntaje_obtenido', 'retroalimentacion']
        widgets = {
            'puntaje_obtenido': forms.NumberInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl',
                'min': 0
            }),
            'retroalimentacion': forms.Textarea(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl',
                'rows': 4,
                'placeholder': 'Retroalimentación para la entrega'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.tarea = kwargs.pop('tarea', None)
        super().__init__(*args, **kwargs)
        if self.tarea is None and getattr(self.instance, 'tarea', None):
            self.tarea = self.instance.tarea

    def clean(self):
        cleaned_data = super().clean()
        puntaje_obtenido = cleaned_data.get('puntaje_obtenido')
        tarea = self.tarea

        if tarea and puntaje_obtenido is not None and puntaje_obtenido > tarea.puntaje_maximo:
            raise forms.ValidationError('El puntaje obtenido no puede ser mayor al puntaje máximo de la tarea.')

        return cleaned_data
