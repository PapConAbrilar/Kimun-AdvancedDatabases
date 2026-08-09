from django import forms

from kimun.forms import FormularioDiccionario


INPUT_CLASS = "input-field w-full px-4 py-3 rounded-xl"


class EventoCalendarioForm(FormularioDiccionario):
    titulo = forms.CharField(widget=forms.TextInput(attrs={"class": INPUT_CLASS}))
    descripcion = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": INPUT_CLASS}))
    tipo = forms.ChoiceField(
        choices=[
            ("clase_deadline", "Plazo de clase"),
            ("evaluacion_deadline", "Plazo de evaluación"),
            ("curso_start", "Inicio de curso"),
            ("curso_end", "Fin de curso"),
            ("evento_general", "Evento general"),
        ]
    )
    fecha_inicio = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    fecha_fin = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    curso = forms.ChoiceField(required=False)
    color = forms.CharField(required=False, initial="#6366f1")

    def __init__(self, *args, cursos=None, **kwargs):
        super().__init__(*args, **kwargs)
        courses = cursos or []
        self.fields["curso"].choices = [("", "Sin curso")] + [
            (course["id"], course["titulo"]) for course in courses
        ]
        self.fields["curso"].queryset = courses

    def clean(self):
        data = super().clean()
        if data.get("fecha_inicio") and data.get("fecha_fin"):
            if data["fecha_fin"] < data["fecha_inicio"]:
                raise forms.ValidationError("La fecha de fin debe ser posterior al inicio.")
        return data
