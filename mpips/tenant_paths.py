from typing import Any, Dict


def tenant_prefix(tenant_id: str) -> str:
    return f"{tenant_id}/"


def validate_tenant_key(tenant_id: str, key: str) -> None:
    normalized_key = key.lstrip("/")
    if not normalized_key.startswith(tenant_prefix(tenant_id)):
        raise ValueError("S3 key is outside the submitted tenant prefix.")


def validate_job_storage_paths(
    tenant_id: str,
    inputs: Dict[str, Any],
    output: Dict[str, Any],
) -> None:
    for node_id, input_config in inputs.items():
        if not isinstance(input_config, dict):
            continue

        key = input_config.get("key")
        if isinstance(key, str) and key:
            try:
                validate_tenant_key(tenant_id, key)
            except ValueError as exc:
                raise ValueError(
                    f"Input node '{node_id}' references a cross-tenant S3 key."
                ) from exc

    output_url = output.get("url")
    if isinstance(output_url, str) and output_url:
        return

    prefix = output.get("prefix")
    if isinstance(prefix, str) and prefix:
        try:
            validate_tenant_key(tenant_id, prefix)
        except ValueError as exc:
            raise ValueError(
                "Output prefix is outside the submitted tenant prefix."
            ) from exc
