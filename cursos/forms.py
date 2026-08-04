from django import forms
from django.conf import settings
from .models import Curso, Material, Categoria, Clase


class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['titulo', 'descripcion', 'categoria', 'estado', 'fecha_limite']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Ej: Primeros Auxilios'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'rows': 4,
                'placeholder': 'Describe el contenido y objetivos del curso...'
            }),
            'categoria': forms.Select(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl'
            }),
            'estado': forms.Select(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl'
            }),
            'fecha_limite': forms.DateTimeInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['categoria'].required = False
        self.fields['fecha_limite'].required = False
        if self.instance and self.instance.fecha_limite:
            self.initial['fecha_limite'] = self.instance.fecha_limite.strftime('%Y-%m-%dT%H:%M')
        
        if self.user and self.user.rol == 'admin':
            from usuarios.models import Usuario
            self.fields['docente_creador'] = forms.ModelChoiceField(
                queryset=Usuario.objects.filter(rol='docente').order_by('first_name', 'last_name'),
                required=True,
                label='Docente Instructor',
                widget=forms.Select(attrs={
                    'class': 'input-field w-full px-4 py-3 rounded-xl'
                })
            )
            self.order_fields(['titulo', 'descripcion', 'categoria', 'estado', 'docente_creador', 'fecha_limite'])


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['titulo', 'tipo', 'archivo', 'url']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Ej: Manual de Primeros Auxilios'
            }),
            'tipo': forms.Select(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl'
            }),
            'archivo': forms.FileInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'accept': '.pdf'
            }),
            'url': forms.URLInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'https://www.youtube.com/watch?v=...'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        archivo = cleaned_data.get('archivo')
        url = cleaned_data.get('url')

        if tipo == 'pdf' and not archivo:
            self.add_error('archivo', 'Debes subir un archivo PDF para este tipo de material.')

        if tipo == 'video' and not url:
            self.add_error('url', 'Debes ingresar una URL de video para este tipo de material.')

        return cleaned_data


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'color', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Ej: Seguridad Laboral'
            }),
            'color': forms.TextInput(attrs={
                'class': 'w-12 h-12 rounded-lg cursor-pointer border-0',
                'type': 'color'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'rows': 3,
                'placeholder': 'Descripción breve de la categoría...'
            }),
        }


class ClaseForm(forms.ModelForm):
    class Meta:
        model = Clase
        fields = ['titulo', 'contenido', 'orden']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Ej: Introducción a los Primeros Auxilios'
            }),
            'orden': forms.NumberInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': '1',
                'min': '1'
            }),
        }

    def clean_orden(self):
        orden = self.cleaned_data.get('orden')
        if orden is not None and orden < 1:
            raise forms.ValidationError('El orden debe ser mayor a 0.')
        return orden

    def clean(self):
        cleaned_data = super().clean()
        titulo = cleaned_data.get('titulo')
        orden = cleaned_data.get('orden')
        curso_obj = cleaned_data.get('curso')
        if not curso_obj:
            curso_obj = getattr(self.instance, 'curso', None)
        curso_id = curso_obj.pk if curso_obj else None

        if titulo and orden and curso_id:
            qs = Clase.objects.filter(curso_id=curso_id, orden=orden)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    {'orden': f'Ya existe una clase con orden {orden} en este curso.'}
                )

        return cleaned_data
