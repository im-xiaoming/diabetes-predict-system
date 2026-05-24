import json
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


DEFAULT_LABELED_CONFIG = {
    "auto_start": True,
    "interval": 5,
    "delay": 3,
}

DEFAULT_UNLABELED_CONFIG = {
    "auto_start": False,
    "interval": 5,
    "delay": 3,
}


def _config_path(name, default_filename):
    return Path(
        getattr(
            settings,
            name,
            settings.BASE_DIR / "configs" / default_filename,
        )
    )


def labeled_config_path():
    return _config_path("MOCK_HIS_LABELED_CONFIG_PATH", "mock_his_labeled_config.json")


def unlabeled_config_path():
    return _config_path("MOCK_HIS_UNLABELED_CONFIG_PATH", "mock_his_unlabeled_config.json")


def _load(path, defaults):
    if not path.exists():
        return dict(defaults)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(defaults)
    merged = dict(defaults)
    merged.update({k: data[k] for k in defaults if k in data})
    return merged


def load_labeled_config():
    return _load(labeled_config_path(), DEFAULT_LABELED_CONFIG)


def load_unlabeled_config():
    return _load(unlabeled_config_path(), DEFAULT_UNLABELED_CONFIG)


class _BaseFeedConfig(models.Model):
    auto_start = models.BooleanField(
        default=True,
        verbose_name="Tự chạy khi khởi động",
        help_text="Tự động chạy luồng feed khi Django khởi động.",
    )
    interval = models.PositiveIntegerField(
        default=5,
        verbose_name="Chu kỳ gửi (giây)",
        help_text="Số giây giữa mỗi lần gửi bản ghi.",
    )
    delay = models.PositiveIntegerField(
        default=3,
        verbose_name="Chờ trước khi bắt đầu (giây)",
        help_text="Số giây chờ trước khi feed bắt đầu sau khi Django sẵn sàng.",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if self.pk is None and type(self).objects.exists():
            raise ValidationError("Only one config of this type can exist.")
        if self.interval < 1:
            raise ValidationError({"interval": "Interval must be at least 1 second."})

    def as_config(self):
        return {
            "auto_start": self.auto_start,
            "interval": self.interval,
            "delay": self.delay,
        }


class LabeledFeedConfig(_BaseFeedConfig):
    auto_start = models.BooleanField(
        default=DEFAULT_LABELED_CONFIG["auto_start"],
        verbose_name="Tự chạy khi khởi động",
        help_text="Tự động chạy luồng feed CÓ NHÃN khi Django khởi động.",
    )
    interval = models.PositiveIntegerField(
        default=DEFAULT_LABELED_CONFIG["interval"],
        verbose_name="Chu kỳ gửi (giây)",
        help_text="Số giây giữa mỗi lần gửi bản ghi (luồng có nhãn).",
    )
    delay = models.PositiveIntegerField(
        default=DEFAULT_LABELED_CONFIG["delay"],
        verbose_name="Chờ trước khi bắt đầu (giây)",
        help_text="Số giây chờ trước khi luồng có nhãn bắt đầu.",
    )

    class Meta:
        verbose_name = "Mock HIS labeled feed config"
        verbose_name_plural = "Mock HIS labeled feed config"

    def __str__(self):
        return f"Labeled feed: {'on' if self.auto_start else 'off'} (every {self.interval}s)"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        path = labeled_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.as_config(), indent=2) + "\n", encoding="utf-8")
        from .feed_runner import labeled_runner
        labeled_runner.apply_config(
            auto_start=self.auto_start,
            interval=self.interval,
            delay=self.delay,
            unlabeled=False,
        )


class UnlabeledFeedConfig(_BaseFeedConfig):
    auto_start = models.BooleanField(
        default=DEFAULT_UNLABELED_CONFIG["auto_start"],
        verbose_name="Tự chạy khi khởi động",
        help_text="Tự động chạy luồng feed KHÔNG NHÃN khi Django khởi động.",
    )
    interval = models.PositiveIntegerField(
        default=DEFAULT_UNLABELED_CONFIG["interval"],
        verbose_name="Chu kỳ gửi (giây)",
        help_text="Số giây giữa mỗi lần gửi bản ghi (luồng không nhãn).",
    )
    delay = models.PositiveIntegerField(
        default=DEFAULT_UNLABELED_CONFIG["delay"],
        verbose_name="Chờ trước khi bắt đầu (giây)",
        help_text="Số giây chờ trước khi luồng không nhãn bắt đầu.",
    )

    class Meta:
        verbose_name = "Mock HIS unlabeled feed config"
        verbose_name_plural = "Mock HIS unlabeled feed config"

    def __str__(self):
        return f"Unlabeled feed: {'on' if self.auto_start else 'off'} (every {self.interval}s)"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        path = unlabeled_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.as_config(), indent=2) + "\n", encoding="utf-8")
        from .feed_runner import unlabeled_runner
        unlabeled_runner.apply_config(
            auto_start=self.auto_start,
            interval=self.interval,
            delay=self.delay,
            unlabeled=True,
        )
