"""Console logging with publication-safe redaction."""

from __future__ import annotations

import logging
import re
import sys

REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"ocid1\.[A-Za-z0-9._-]+"), "[REDACTED-OCI-ID]"),
    (re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)"), "[REDACTED-IP]"),
    (re.compile(r"(?:[A-Fa-f0-9]{2}:){15}[A-Fa-f0-9]{2}"), "[REDACTED-FINGERPRINT]"),
    (re.compile(r"(?i)authorization\s*[:=]\s*\S+"), "authorization=[REDACTED]"),
    (
        re.compile(r"/(?:root|home)/\S+\.(?:pem|key)(?=\s|$)", re.IGNORECASE),
        "[REDACTED-KEY-PATH]",
    ),
)


def redact(value: object) -> str:
    text = str(value)
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def configure_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("oci_a1_flex_hunter")
    logger.handlers.clear()
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(RedactingFormatter("level=%(levelname)s event=%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger
