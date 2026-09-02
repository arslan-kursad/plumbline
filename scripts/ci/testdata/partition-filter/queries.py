"""Fixture corpus for the partition-filter check. Not executed; only parsed.

Six cases, one per class the checker distinguishes, so a change that collapses two
classes into one fails here rather than in review.
"""

PROJECT = "plumbline-local"
DATASET = "plumbline"


def filtered():
    return (
        f"SELECT * FROM `{PROJECT}.{DATASET}.spans_deduped` "
        "WHERE start_time >= TIMESTAMP('2020-01-01')"
    )


def unfiltered():
    # The case the check exists for: a new read that forgets the predicate.
    return f"SELECT COUNT(*) FROM `{PROJECT}.{DATASET}.spans_real`"


def interpolated_view_name(view):
    # The table name does not survive interpolation; the dataset does, so this is a site.
    return f"SELECT * FROM `{PROJECT}.plumbline.{view}` WHERE start_time > '2020-01-01'"


def interpolated_predicate(where):
    # start_time lives in the caller. Unverifiable here, and not a failure.
    return f"SELECT * FROM `{PROJECT}.{DATASET}.spans` WHERE {where}"


def deliberately_unfiltered():
    # partition-filter: intentionally-absent -- a fixture for the declared case.
    return f"SELECT 1 FROM `{PROJECT}.{DATASET}.spans`"


def not_a_span_query():
    return f"SELECT * FROM `{PROJECT}.{DATASET}.something_else`"
