"""Narrow production boundary around the official OCI Python SDK."""

from __future__ import annotations

from typing import Any, NoReturn

from .config import HunterConfig
from .errors import (
    AuthenticationError,
    AuthorizationError,
    CapacityUnavailableError,
    MalformedRequestError,
    NonRetryableOCIError,
    TransientOCIError,
)
from .models import HunterConfigProtocol, LaunchResult

PROJECT_TAG_KEY = "sagneo-project"
MATCHING_STATES = {"PROVISIONING", "STARTING", "RUNNING", "STOPPING", "STOPPED"}


class OCIComputeAdapter:
    """Use OCI Compute without exposing SDK objects to controller code."""

    def __init__(self, config: HunterConfig) -> None:
        try:
            import oci

            sdk_config = oci.config.from_file(
                file_location=str(config.oci_config_file), profile_name=config.oci_profile
            )
            self._oci = oci
            self._client = oci.core.ComputeClient(sdk_config)
        except Exception as exc:
            self._raise_translated(exc)

    def matching_instance_exists(self, config: HunterConfigProtocol) -> bool:
        try:
            response = self._oci.pagination.list_call_get_all_results(
                self._client.list_instances,
                compartment_id=config.compartment_id,
            )
        except Exception as exc:
            self._raise_translated(exc)
        return any(self._is_match(instance, config) for instance in response.data)

    @staticmethod
    def _is_match(instance: Any, config: HunterConfigProtocol) -> bool:
        return bool(
            instance.display_name == config.display_name
            and (instance.freeform_tags or {}).get(PROJECT_TAG_KEY) == config.project_tag
            and instance.lifecycle_state in MATCHING_STATES
        )

    def launch_instance(self, config: HunterConfigProtocol, retry_token: str) -> LaunchResult:
        ssh_key = config.ssh_public_key_path.read_text(encoding="utf-8").strip()
        source_kwargs: dict[str, Any] = {
            "source_type": "image",
            "image_id": config.image_id,
        }
        if config.boot_volume_size_gb is not None:
            source_kwargs["boot_volume_size_in_gbs"] = config.boot_volume_size_gb

        models = self._oci.core.models
        details = models.LaunchInstanceDetails(
            availability_domain=config.availability_domain,
            compartment_id=config.compartment_id,
            display_name=config.display_name,
            shape=config.shape,
            shape_config=models.LaunchInstanceShapeConfigDetails(
                ocpus=config.ocpus,
                memory_in_gbs=config.memory_gb,
            ),
            source_details=models.InstanceSourceViaImageDetails(**source_kwargs),
            create_vnic_details=models.CreateVnicDetails(subnet_id=config.subnet_id),
            metadata={"ssh_authorized_keys": ssh_key},
            freeform_tags={PROJECT_TAG_KEY: config.project_tag},
        )
        try:
            self._client.launch_instance(
                launch_instance_details=details,
                # OCI documents a 24-hour retry-token lifetime. The controller owns
                # this token so every retry of one logical submission reuses it.
                opc_retry_token=retry_token,
            )
        except Exception as exc:
            self._raise_translated(exc)
        return LaunchResult()

    @staticmethod
    def _raise_translated(exc: Exception) -> NoReturn:
        status = getattr(exc, "status", None)
        code = str(getattr(exc, "code", "")).lower()
        message = str(getattr(exc, "message", "")).lower()
        class_name = type(exc).__name__.lower()
        combined = f"{code} {message}"

        if status == 401 or "config" in class_name:
            raise AuthenticationError("OCI authentication configuration was rejected") from exc
        if status == 403:
            raise AuthorizationError("OCI authorization was denied") from exc
        if "outofhostcapacity" in combined or "capacity" in combined:
            raise CapacityUnavailableError("OCI reported unavailable capacity") from exc
        if status == 400:
            raise MalformedRequestError("OCI rejected the launch request") from exc
        if status == 429 or (isinstance(status, int) and status >= 500):
            raise TransientOCIError("OCI reported a transient service failure") from exc
        raise NonRetryableOCIError("OCI request failed and will not be retried") from exc
