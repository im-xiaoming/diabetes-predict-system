from django import forms


class TrainModelForm(forms.Form):
    tune = forms.BooleanField(
        required=False,
        initial=True,
        label="Tune bằng Optuna"
    )

    n_trials = forms.IntegerField(
        min_value=1,
        initial=5,
        label="Số trials"
    )

    timeout = forms.IntegerField(
        min_value=1,
        initial=600,
        label="Timeout mỗi model (giây)"
    )

    register = forms.BooleanField(
        required=False,
        initial=True,
        label="Register best model vào MLflow"
    )