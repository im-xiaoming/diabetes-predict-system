from pathlib import Path
import argparse
import logging
import sys
import time

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.preprocessing import FT, TG, rename_cols


LOGGER = logging.getLogger("ml.export_training_data")

DEFAULT_OUTPUT = ROOT_DIR / "data" / "training.csv"
DEFAULT_FALLBACK = ROOT_DIR / "data" / "data.csv"

TRAINING_COLUMNS = [
    "SL.NO",
    "NAME",
    "AGE",
    "SEX",
    "BMI",
    "SP",
    "BP",
    "HbA1c",
    "FPS",
    "PPS",
    "FAMILY H/O",
    "ONSET AGE",
    "DIA LIFE",
    "SMOKING",
    "PHY ACT",
    "MED USE",
    "MED ADH",
    "NEP",
    "NEU",
    "RET",
    "CV",
    "PER VAS",
]


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
        force=True,
    )


def setup_django():
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "diabetes_predict_system.settings")
    import django

    django.setup()
    from django.conf import settings

    db_name = settings.DATABASES.get("default", {}).get("NAME", "unknown")
    LOGGER.info("django_ready database=%s", db_name)


def sex_value(value):
    return 0 if value == "female" else 1


def bool_int(value):
    return int(bool(value))


def export_rows():
    from patients.models import ClinicalRecord

    records = (
        ClinicalRecord.objects.filter(label__isnull=False)
        .select_related("patient", "label")
        .order_by("id")
    )
    record_count = records.count()
    LOGGER.info("db_query_ready labeled_records=%s", record_count)
    rows = []
    for record in records:
        label = record.label
        rows.append(
            {
                "SL.NO": record.patient_id,
                "NAME": record.patient.name,
                "AGE": record.age,
                "SEX": sex_value(record.patient.sex),
                "BMI": record.bmi,
                "SP": record.sp,
                "BP": record.bp,
                "HbA1c": record.hba1c,
                "FPS": record.fps,
                "PPS": record.pps,
                "FAMILY H/O": record.fam_ho,
                "ONSET AGE": record.on_age,
                "DIA LIFE": record.dia_life,
                "SMOKING": record.smk,
                "PHY ACT": record.phy_act,
                "MED USE": record.med_use,
                "MED ADH": record.med_adh,
                "NEP": bool_int(label.nep),
                "NEU": bool_int(label.neu),
                "RET": bool_int(label.ret),
                "CV": bool_int(label.cv),
                "PER VAS": bool_int(label.per_vas),
            }
        )
    return rows


def target_positive_counts(df):
    counts = {}
    for col in TG:
        if col not in df.columns:
            continue
        counts[col] = int(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())
    return counts


def write_training_csv(output, fallback):
    started_at = time.monotonic()
    LOGGER.info("export_start output=%s fallback=%s", output, fallback)
    setup_django()
    output = Path(output)
    fallback = Path(fallback) if fallback else None
    output.parent.mkdir(parents=True, exist_ok=True)

    rows = export_rows()
    frames = []
    fallback_rows = 0
    if fallback and fallback.exists():
        LOGGER.info("fallback_read_start path=%s", fallback)
        fallback_df = rename_cols(pd.read_csv(fallback))
        fallback_df = fallback_df[[col for col in TRAINING_COLUMNS if col in fallback_df.columns]]
        frames.append(fallback_df)
        fallback_rows = len(fallback_df)
        LOGGER.info(
            "fallback_read_done rows=%s columns=%s",
            fallback_rows,
            list(fallback_df.columns),
        )
    elif fallback:
        LOGGER.warning("fallback_missing path=%s", fallback)

    if rows:
        frames.append(pd.DataFrame(rows, columns=TRAINING_COLUMNS))

    if frames:
        training_df = pd.concat(frames, ignore_index=True)
        before_dedup = len(training_df)
        training_df = training_df.drop_duplicates(subset=FT + TG).reset_index(drop=True)
        duplicates_dropped = before_dedup - len(training_df)
    else:
        training_df = pd.DataFrame(columns=TRAINING_COLUMNS)
        before_dedup = 0
        duplicates_dropped = 0

    training_df.to_csv(output, index=False)
    output_size = output.stat().st_size if output.exists() else 0
    LOGGER.info("fallback_rows=%s", fallback_rows)
    LOGGER.info("db_labeled_rows=%s", len(rows))
    LOGGER.info("training_rows_before_dedup=%s", before_dedup)
    LOGGER.info("duplicates_dropped=%s", duplicates_dropped)
    LOGGER.info("training_rows=%s", len(training_df))
    LOGGER.info("target_positive_counts=%s", target_positive_counts(training_df))
    LOGGER.info("output=%s bytes=%s", output, output_size)
    LOGGER.info("export_done duration_sec=%.2f", time.monotonic() - started_at)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Training CSV output path")
    parser.add_argument("--fallback", default=str(DEFAULT_FALLBACK), help="Seed CSV merged before DB labeled records")
    return parser.parse_args()


if __name__ == "__main__":
    configure_logging()
    args = parse_args()
    write_training_csv(args.output, args.fallback)
