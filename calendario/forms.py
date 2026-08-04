from django import forms
from .models import EventoCalendario, TipoEvento
from cursos.models import Curso
from datetime import datetime


class EventoCalendarioForm(forms.ModelForm):
    class Meta:
        model = EventoCalendario
        fields = ['titulo', 'descripcion', 'tipo', 'fecha_inicio', 'fecha_fin', 'curso', 'color']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Título del evento'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl',
                'rows': 3,
                'placeholder': 'Descripción opcional'
            }),
            'tipo': forms.Select(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl'
            }),
            'fecha_inicio': forms.DateTimeInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'fecha_fin': forms.DateTimeInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'curso': forms.Select(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl'
            }),
            'color': forms.TextInput(attrs={
                'class': 'w-12 h-12 rounded-lg cursor-pointer border-0',
                'type': 'color'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['curso'].required = False
        self.fields['descripcion'].required = False
        self.fields['color'].required = False
        if self.instance and self.instance.fecha_inicio:
            self.initial['fecha_inicio'] = self.instance.fecha_inicio.strftime('%Y-%m-%dT%H:%M')
        if self.instance and self.instance.fecha_fin:
            self.initial['fecha_fin'] = self.instance.fecha_fin.strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')

        if fecha_inicio and fecha_fin:
            if fecha_fin < fecha_inicio:
                raise forms.ValidationError('La fecha de fin debe ser posterior a la fecha de inicio.')

        return cleaned_data
