from types import SimpleNamespace

from django import forms


class FormularioDiccionario(forms.Form):
    """Formulario sin ORM que acepta un diccionario como instancia inicial."""

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None) or {}
        initial = {**instance, **kwargs.pop("initial", {})}
        for key, value in list(initial.items()):
            if hasattr(value, "strftime"):
                initial[key] = value.strftime("%Y-%m-%dT%H:%M")
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        self.instance_data = instance
        self.instance = SimpleNamespace(
            **{**instance, "pk": instance.get("pk"), "id": instance.get("id")}
        )
