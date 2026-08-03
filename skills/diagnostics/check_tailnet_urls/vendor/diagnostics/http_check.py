"""HTTP reachability probes (stdlib only)."""

from __future__ import annotations

import socket
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable


# Auth walls and redirects still mean the edge/service answered.
REACHABLE_STATUSES = set(range(200, 400)) | {401, 403}


@dataclass(frozen=True)
class ProbeResult:
    reachable: bool
    status_code: int | None
    error: str | None
    final_url: str | None = None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Keep 3xx as the response so oauth2-proxy → Authentik counts as reachable."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ARG002
        return None


def _opener(verify_tls: bool) -> urllib.request.OpenerDirector:
    handlers: list[urllib.request.BaseHandler] = [_NoRedirect()]
    if not verify_tls:
        handlers.append(
            urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
        )
    opener = urllib.request.build_opener(*handlers)
    opener.addheaders = [("User-Agent", "openclaw-diagnostics/0.1")]
    return opener


def probe_url(
    url: str,
    *,
    timeout: float = 5.0,
    method: str = "GET",
    verify_tls: bool = True,
) -> ProbeResult:
    """Probe a URL once.

    Reachable = TCP/TLS success and HTTP status in 2xx/3xx, or 401/403
    (service up behind auth). Connection failures and timeouts are unreachable.
    """
    opener = _opener(verify_tls)
    req = urllib.request.Request(url, method=method.upper())
    previous = socket.getdefaulttimeout()
    try:
        # Also bounds DNS / connect hangs that ignore per-request timeout on some platforms.
        socket.setdefaulttimeout(timeout)
        with opener.open(req, timeout=timeout) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
            code_i = int(code) if code is not None else None
            return ProbeResult(
                reachable=code_i in REACHABLE_STATUSES if code_i is not None else False,
                status_code=code_i,
                error=None,
                final_url=resp.geturl(),
            )
    except urllib.error.HTTPError as exc:
        code = int(exc.code)
        return ProbeResult(
            reachable=code in REACHABLE_STATUSES,
            status_code=code,
            error=None if code in REACHABLE_STATUSES else f"HTTP {code}",
            final_url=getattr(exc, "url", None) or url,
        )
    except Exception as exc:  # noqa: BLE001
        return ProbeResult(
            reachable=False,
            status_code=None,
            error=f"{type(exc).__name__}: {exc}",
            final_url=None,
        )
    finally:
        socket.setdefaulttimeout(previous)


ProbeFn = Callable[..., ProbeResult]
