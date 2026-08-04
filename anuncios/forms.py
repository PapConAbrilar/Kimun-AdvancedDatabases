from django import forms

from .models import Anuncio


class AnuncioForm(forms.ModelForm):
    class Meta:
        model = Anuncio
        fields = [
            'titulo',
            'contenido',
            'prioridad',
            'curso',
            'publicado',
            'fecha_publicacion',
            'fecha_expiracion',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'input-field w-full px-4 py-3 rounded-xl'}),
            'contenido': forms.Textarea(attrs={'class': 'input-field w-full px-4 py-3 rounded-xl', 'rows': 5}),
            'prioridad': forms.Select(attrs={'class': 'input-field w-full px-4 py-3 rounded-xl'}),
            'curso': forms.Select(attrs={'class': 'input-field w-full px-4 py-3 rounded-xl'}),
            'publicado': forms.CheckboxInput(attrs={'class': 'input-field'}),
            'fecha_publicacion': forms.DateTimeInput(
                attrs={'class': 'input-field w-full px-4 py-3 rounded-xl', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'fecha_expiracion': forms.DateTimeInput(
                attrs={'class': 'input-field w-full px-4 py-3 rounded-xl', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['curso'].required = False
        if self.instance and self.instance.fecha_publicacion:
            self.initial['fecha_publicacion'] = self.instance.fecha_publicacion.strftime('%Y-%m-%dT%H:%M')
        if self.instance and self.instance.fecha_expiracion:
            self.initial['fecha_expiracion'] = self.instance.fecha_expiracion.strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        cleaned_data = super().clean()
        fecha_publicacion = cleaned_data.get('fecha_publicacion')
        fecha_expiracion = cleaned_data.get('fecha_expiracion')

        if fecha_publicacion and fecha_expiracion and fecha_expiracion <= fecha_publicacion:
            raise forms.ValidationError('La fecha de expiración debe ser posterior a la fecha de publicación.')

        return cleaned_data
