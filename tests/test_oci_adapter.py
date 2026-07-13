from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

import pytest

from oci_a1_flex_hunter.config import HunterConfig
from oci_a1_flex_hunter.errors import (
    AuthenticationError,
    AuthorizationError,
    CapacityUnavailableError,
    MalformedRequestError,
    NonRetryableOCIError,
    TransientOCIError,
)
from oci_a1_flex_hunter.oci_adapter import PROJECT_TAG_KEY, OCIComputeAdapter


class Model:
    def __init__(self, **values: Any) -> None:
        self.__dict__.update(values)


class Client:
    def __init__(self, sdk_config: object | None = None) -> None:
        self.sdk_config = sdk_config
        self.launches: list[dict[str, object]] = []
        self.instances: list[object] = []

    def launch_instance(self, **kwargs: object) -> None:
        self.launches.append(kwargs)

    def list_instances(self, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(data=self.instances)


def fake_sdk(client: Client) -> SimpleNamespace:
    models = SimpleNamespace(
        LaunchInstanceDetails=Model,
        LaunchInstanceShapeConfigDetails=Model,
        InstanceSourceViaImageDetails=Model,
        CreateVnicDetails=Model,
    )
    pagination = SimpleNamespace(list_call_get_all_results=lambda call, **kwargs: call(**kwargs))
    return SimpleNamespace(core=SimpleNamespace(models=models), pagination=pagination)


def adapter_with(client: Client) -> OCIComputeAdapter:
    adapter = OCIComputeAdapter.__new__(OCIComputeAdapter)
    adapter._oci = fake_sdk(client)
    adapter._client = client
    return adapter


def test_sdk_profile_is_loaded(monkeypatch: pytest.MonkeyPatch, config: HunterConfig) -> None:
    calls: list[dict[str, str]] = []
    client = Client()

    def from_file(**kwargs: str) -> dict[str, str]:
        calls.append(kwargs)
        return {"synthetic": "profile"}

    sdk = fake_sdk(client)
    sdk.config = SimpleNamespace(from_file=from_file)
    sdk.core.ComputeClient = lambda loaded: client
    monkeypatch.setitem(sys.modules, "oci", sdk)

    adapter = OCIComputeAdapter(config)
    assert adapter._client is client
    assert calls == [
        {"file_location": str(config.oci_config_file), "profile_name": config.oci_profile}
    ]


def test_sdk_profile_loading_error_is_translated(
    monkeypatch: pytest.MonkeyPatch, config: HunterConfig
) -> None:
    def rejected(**kwargs: str) -> None:
        del kwargs
        raise ConfigFixtureError("sensitive-fixture-value")

    sdk = fake_sdk(Client())
    sdk.config = SimpleNamespace(from_file=rejected)
    monkeypatch.setitem(sys.modules, "oci", sdk)
    with pytest.raises(AuthenticationError) as raised:
        OCIComputeAdapter(config)
    assert "sensitive-fixture-value" not in str(raised.value)


def test_launch_payload_propagates_all_fields(config: HunterConfig) -> None:
    client = Client()
    adapter = adapter_with(client)
    adapter.launch_instance(config, "stable-retry-token")

    assert len(client.launches) == 1
    call = client.launches[0]
    assert call["opc_retry_token"] == "stable-retry-token"
    details = call["launch_instance_details"]
    assert isinstance(details, Model)
    assert details.compartment_id == config.compartment_id
    assert details.availability_domain == config.availability_domain
    assert details.display_name == config.display_name
    assert details.shape == config.shape
    assert details.shape_config.ocpus == config.ocpus
    assert details.shape_config.memory_in_gbs == config.memory_gb
    assert details.source_details.image_id == config.image_id
    assert details.create_vnic_details.subnet_id == config.subnet_id
    assert details.metadata["ssh_authorized_keys"] == "ssh-ed25519 AAAA synthetic-test"
    assert details.freeform_tags == {PROJECT_TAG_KEY: config.project_tag}


def test_launch_payload_propagates_boot_volume(config: HunterConfig) -> None:
    client = Client()
    adapter = adapter_with(client)
    changed = SimpleNamespace(**{field: getattr(config, field) for field in config.__slots__})
    changed.boot_volume_size_gb = 50
    adapter.launch_instance(changed, "token")
    details = client.launches[0]["launch_instance_details"]
    assert isinstance(details, Model)
    assert details.source_details.boot_volume_size_in_gbs == 50


def test_matching_instance_list_is_read_only(config: HunterConfig) -> None:
    client = Client()
    client.instances = [
        SimpleNamespace(
            display_name=config.display_name,
            freeform_tags={PROJECT_TAG_KEY: config.project_tag},
            lifecycle_state="RUNNING",
        )
    ]
    assert adapter_with(client).matching_instance_exists(config)


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"display_name": "different"}, False),
        ({"freeform_tags": {PROJECT_TAG_KEY: "different"}}, False),
        ({"freeform_tags": None}, False),
        ({"lifecycle_state": "TERMINATED"}, False),
        ({}, True),
    ],
)
def test_match_requires_exact_identity_and_active_state(
    config: HunterConfig, changes: dict[str, object], expected: bool
) -> None:
    values: dict[str, object] = {
        "display_name": config.display_name,
        "freeform_tags": {PROJECT_TAG_KEY: config.project_tag},
        "lifecycle_state": "RUNNING",
    }
    values.update(changes)
    assert OCIComputeAdapter._is_match(SimpleNamespace(**values), config) is expected


class SDKError(Exception):
    def __init__(self, status: int | None, code: str = "", message: str = "") -> None:
        self.status = status
        self.code = code
        self.message = message


class ConfigFixtureError(Exception):
    pass


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (SDKError(401), AuthenticationError),
        (SDKError(403), AuthorizationError),
        (SDKError(400), MalformedRequestError),
        (SDKError(429), TransientOCIError),
        (SDKError(500), TransientOCIError),
        (SDKError(503), TransientOCIError),
        (SDKError(409, "OutOfHostCapacity"), CapacityUnavailableError),
        (ConfigFixtureError("synthetic"), AuthenticationError),
        (SDKError(418), NonRetryableOCIError),
    ],
)
def test_sdk_errors_are_translated_and_sanitized(
    error: Exception, expected: type[Exception]
) -> None:
    marker = "sensitive-fixture-value"
    if isinstance(error, SDKError):
        error.message = marker if not error.message else error.message
    with pytest.raises(expected) as raised:
        OCIComputeAdapter._raise_translated(error)
    assert marker not in str(raised.value)


def test_list_error_is_translated(config: HunterConfig) -> None:
    client = Client()

    def rejected(**kwargs: object) -> None:
        raise SDKError(403, message="sensitive-fixture-value")

    client.list_instances = rejected  # type: ignore[method-assign]
    with pytest.raises(AuthorizationError, match="authorization"):
        adapter_with(client).matching_instance_exists(config)


def test_launch_error_is_translated(config: HunterConfig) -> None:
    client = Client()

    def rejected(**kwargs: object) -> None:
        raise SDKError(503, message="sensitive-fixture-value")

    client.launch_instance = rejected  # type: ignore[method-assign]
    with pytest.raises(TransientOCIError, match="transient"):
        adapter_with(client).launch_instance(config, "stable-token")
