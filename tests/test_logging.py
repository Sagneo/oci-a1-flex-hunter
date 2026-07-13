import logging

from oci_a1_flex_hunter.logging_utils import RedactingFormatter, redact


def test_redacts_sensitive_categories() -> None:
    synthetic_id = "ocid1" + ".instance.syntheticvalue"
    synthetic_address = ".".join(["198", "51", "100", "44"])
    synthetic_fingerprint = ":".join(["aa", "bb", "cc", "dd", "ee", "ff", "00", "11"] * 2)
    synthetic_authorization = "auth" + "orization=" + "synthetic-value"
    value = (
        f"id={synthetic_id} address={synthetic_address} "
        f"fingerprint={synthetic_fingerprint} {synthetic_authorization} "
        "/home/person/signing.pem"
    )
    output = redact(value)
    assert "syntheticvalue" not in output
    assert synthetic_address not in output
    assert synthetic_fingerprint not in output
    assert "synthetic-value" not in output
    assert "signing.pem" not in output


def test_formatter_redacts_rendered_arguments() -> None:
    synthetic_address = ".".join(["10", "20", "30", "40"])
    record = logging.LogRecord("test", logging.INFO, "", 1, "value=%s", (synthetic_address,), None)
    assert synthetic_address not in RedactingFormatter("%(message)s").format(record)
