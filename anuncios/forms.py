from django import forms

from kimun.forms import FormularioDiccionario


INPUT_CLASS = "input-field w-full px-4 py-3 rounded-xl"


class AnuncioForm(FormularioDiccionario):
    titulo = forms.CharField(widget=forms.TextInput(attrs={"class": INPUT_CLASS}))
    contenido = forms.CharField(widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 5}))
    prioridad = forms.ChoiceField(
        choices=[
            ("info", "Informativo"),
            ("aviso", "Aviso"),
            ("importante", "Importante"),
            ("urgente", "Urgente"),
        ]
    )
    curso = forms.ChoiceField(required=False)
    publicado = forms.BooleanField(required=False)
    fecha_publicacion = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    fecha_expiracion = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))

    def __init__(self, *args, cursos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["curso"].choices = [("", "General")] + [
            (course["id"], course["titulo"]) for course in (cursos or [])
        ]

    def clean(self):
        data = super().clean()
        if data.get("fecha_publicacion") and data.get("fecha_expiracion"):
            if data["fecha_expiracion"] <= data["fecha_publicacion"]:
                raise forms.ValidationError("La expiración debe ser posterior a la publicación.")
        return data
