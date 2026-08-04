from django import forms
from .models import Evaluacion, BancoPreguntas


class BancoPreguntasForm(forms.ModelForm):
    class Meta:
        model = BancoPreguntas
        fields = ['nombre', 'descripcion', 'curso', 'es_publico']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg input-field',
                'placeholder': 'Ej: Banco de Preguntas - Módulo 1'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg input-field',
                'rows': 3,
                'placeholder': 'Descripción opcional del banco de preguntas'
            }),
            'curso': forms.Select(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl'
            }),
            'es_publico': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['curso'].required = False
        self.fields['descripcion'].required = False


class EvaluacionForm(forms.ModelForm):
    duracion_minutos = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg input-field',
            'min': 1,
            'placeholder': 'Sin límite'
        }),
        help_text='Tiempo máximo para responder en minutos.'
    )
    max_intentos = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg input-field',
            'min': 0,
            'placeholder': '0 = sin límite'
        }),
        help_text='Cantidad máxima de intentos permitidos. Usa 0 para sin límite.'
    )
    preguntas_por_intento = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg input-field',
            'min': 1,
            'placeholder': 'Todas las preguntas'
        }),
        help_text='Número de preguntas aleatorias a mostrar por intento. Déjalo vacío para usar todas.'
    )

    class Meta:
        model = Evaluacion
        fields = ['titulo', 'porcentaje_aprobacion', 'max_intentos', 'duracion_minutos', 'preguntas_por_intento']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg input-field',
                'placeholder': 'Ej: Evaluación Final - Módulo 1'
            }),
            'porcentaje_aprobacion': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg input-field',
                'min': 0,
                'max': 100
            }),
        }

    def clean_porcentaje_aprobacion(self):
        porcentaje = self.cleaned_data.get('porcentaje_aprobacion')
        if porcentaje is None:
            raise forms.ValidationError('El porcentaje de aprobación es obligatorio.')
        if porcentaje < 0 or porcentaje > 100:
            raise forms.ValidationError('El porcentaje debe estar entre 0 y 100.')
        return porcentaje

    def clean_max_intentos(self):
        max_intentos = self.cleaned_data.get('max_intentos')
        return 0 if max_intentos in (None, '') else max_intentos

    def clean_duracion_minutos(self):
        duracion = self.cleaned_data.get('duracion_minutos')
        return None if duracion in (None, '') else duracion

    def clean_preguntas_por_intento(self):
        preguntas_por_intento = self.cleaned_data.get('preguntas_por_intento')
        return None if preguntas_por_intento in (None, '') else preguntas_por_intento
