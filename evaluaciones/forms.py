from django import forms

from kimun.forms import FormularioDiccionario


INPUT_CLASS = "input-field w-full px-4 py-3 rounded-xl"


class BancoPreguntasForm(FormularioDiccionario):
    nombre = forms.CharField(widget=forms.TextInput(attrs={"class": INPUT_CLASS}))
    descripcion = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": INPUT_CLASS}))
    curso = forms.ChoiceField(required=False, widget=forms.Select(attrs={"class": INPUT_CLASS}))
    es_publico = forms.BooleanField(required=False)

    def __init__(self, *args, cursos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["curso"].choices = [("", "General")] + [
            (course["id"], course["titulo"]) for course in (cursos or [])
        ]


class EvaluacionForm(FormularioDiccionario):
    titulo = forms.CharField(widget=forms.TextInput(attrs={"class": INPUT_CLASS}))
    porcentaje_aprobacion = forms.IntegerField(min_value=0, max_value=100, initial=70)
    max_intentos = forms.IntegerField(min_value=0, required=False, initial=0)
    duracion_minutos = forms.IntegerField(min_value=1, required=False)
    preguntas_por_intento = forms.IntegerField(min_value=1, required=False)

    def clean_max_intentos(self):
        return self.cleaned_data.get("max_intentos") or 0
