"""Normalized Coolify and Tailscale resource models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CoolifyResource:
    id: str
    name: str
    resource_type: str
    project: str | None = None
    environment: str | None = None
    status: str | None = None
    tags: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    service_name: str | None = None


@dataclass
class TailscaleResource:
    hostname: str
    id: str | None = None
    dns_name: str | None = None
    online: bool | None = None
    tags: list[str] = field(default_factory=list)


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value if x is not None]
    if isinstance(value, str):
        return [value]
    return []


def _as_str_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in value.items():
        if v is None:
            continue
        out[str(k)] = str(v)
    return out


def coolify_from_dict(data: dict[str, Any]) -> CoolifyResource:
    rid = data.get("id") or data.get("uuid")
    name = data.get("name")
    if not rid or not name:
        raise ValueError(f"Coolify resource missing id/name: {data!r}")
    resource_type = str(
        data.get("resource_type") or data.get("type") or "application"
    )
    return CoolifyResource(
        id=str(rid),
        name=str(name),
        resource_type=resource_type,
        project=_optional_str(data.get("project")),
        environment=_optional_str(data.get("environment")),
        status=_optional_str(data.get("status")),
        tags=_as_str_list(data.get("tags")),
        labels=_as_str_dict(data.get("labels")),
        service_name=_optional_str(data.get("service_name") or data.get("service")),
    )


def tailscale_from_dict(data: dict[str, Any]) -> TailscaleResource:
    hostname = data.get("hostname")
    if not hostname:
        raise ValueError(f"Tailscale resource missing hostname: {data!r}")
    dns = data.get("dns_name") or data.get("name")
    dns_name = str(dns) if dns else None
    # Prefer FQDN-looking name as dns_name
    if dns_name and "." not in dns_name and data.get("dns_name"):
        dns_name = str(data["dns_name"])
    online = data.get("online")
    if online is not None and not isinstance(online, bool):
        online = str(online).lower() in {"1", "true", "yes", "online"}
    return TailscaleResource(
        id=_optional_str(data.get("id") or data.get("node_id")),
        hostname=str(hostname),
        dns_name=dns_name,
        online=online,
        tags=_as_str_list(data.get("tags")),
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


class CoolifyAdapter:
    """Normalize agent-written Coolify JSON into CoolifyResource list."""

    def collect_resources(self, data: Any) -> list[CoolifyResource]:
        raw_list = self._extract_list(data)
        resources: list[CoolifyResource] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            resources.append(coolify_from_dict(item))
        return resources

    @staticmethod
    def _extract_list(data: Any) -> list[Any]:
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            raise ValueError("Coolify input must be a JSON object or array")
        if "resources" in data:
            resources = data["resources"]
            if not isinstance(resources, list):
                raise ValueError("'resources' must be a list")
            return resources
        # Flatten hierarchical coolify-inventory shape if provided
        projects = data.get("projects")
        if isinstance(projects, list):
            flat: list[dict[str, Any]] = []
            for project in projects:
                if not isinstance(project, dict):
                    continue
                pname = project.get("name")
                for env in project.get("environments") or []:
                    if not isinstance(env, dict):
                        continue
                    ename = env.get("name")
                    for key, rtype in (
                        ("applications", "application"),
                        ("services", "service"),
                        ("databases", "database"),
                    ):
                        for res in env.get(key) or []:
                            if not isinstance(res, dict):
                                continue
                            item = dict(res)
                            item.setdefault("project", pname)
                            item.setdefault("environment", ename)
                            item.setdefault("resource_type", rtype)
                            flat.append(item)
            return flat
        raise ValueError("Coolify input missing 'resources' (or hierarchical 'projects')")


class TailscaleAdapter:
    """Normalize agent-written Tailscale JSON into TailscaleResource list."""

    def collect_resources(self, data: Any) -> list[TailscaleResource]:
        devices = self._extract_devices(data)
        out: list[TailscaleResource] = []
        for item in devices:
            if not isinstance(item, dict):
                continue
            out.append(tailscale_from_dict(item))
        return out

    @staticmethod
    def _extract_devices(data: Any) -> list[Any]:
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            raise ValueError("Tailscale input must be a JSON object or array")
        if "devices" in data:
            devices = data["devices"]
            if not isinstance(devices, list):
                raise ValueError("'devices' must be a list")
            return devices
        raise ValueError("Tailscale input missing 'devices'")
