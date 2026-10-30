"""Web GUI QR preview/submit helpers.

Supports single-account and multi-account ("help classmates") submission.
"""

from __future__ import annotations

import hashlib
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from troTHU.app_qr_experience import build_qr_scan_view_state, sanitize_qr_scan_result

Submitter = Callable[..., Awaitable[Mapping[str, Any]]]
Previewer = Callable[[str], Mapping[str, Any]]


def qr_payload_hash(payload: str) -> str:
    text = str(payload or "").strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _as_mapping(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {"ok": bool(value)}


def build_web_gui_qr_preview(payload: str, *, previewer: Previewer) -> Dict[str, Any]:
    text = str(payload or "").strip()
    if not text:
        result = {
            "ok": False,
            "status": "empty_payload",
            "error": "沒有 QR 內容。",
            "match_count": 0,
        }
        result["view_state"] = build_qr_scan_view_state(preview=result, fanout=False)
        return sanitize_qr_scan_result(result)
    preview = _as_mapping(previewer(text))
    digest = qr_payload_hash(text)
    preview.setdefault("payload_hash", digest)
    preview["qr_hash"] = digest
    preview["fanout"] = False
    preview["view_state"] = build_qr_scan_view_state(preview=preview, fanout=False)
    return sanitize_qr_scan_result(preview)


async def _call_submitter(submitter: Submitter, *args: Any) -> Mapping[str, Any]:
    result = submitter(*args)
    if hasattr(result, "__await__"):
        result = await result
    return _as_mapping(result)


async def run_single_account_qr_submit(
    payload: str,
    *,
    has_credentials: bool,
    last_success_hash: str = "",
    in_flight: bool = False,
    submitter: Optional[Submitter] = None,
    previewer: Optional[Previewer] = None,
    fanout: bool = False,
    fanout_all: bool = False,
    **kwargs: Any,
) -> Tuple[Dict[str, Any], str]:
    """Backward-compatible single-account submit (fanout ignored)."""
    del fanout, fanout_all, kwargs
    return await run_web_gui_qr_submit(
        payload,
        has_credentials=has_credentials,
        last_success_hash=last_success_hash,
        in_flight=in_flight,
        mode="single",
        accounts=None,
        submitter=submitter,
        previewer=previewer,
    )


async def run_multi_account_qr_submit(
    payload: str,
    *,
    accounts: Optional[Sequence[str]] = None,
    in_flight: bool = False,
    submitter: Optional[Submitter] = None,
    previewer: Optional[Previewer] = None,
) -> Tuple[Dict[str, Any], Optional[str]]:
    text = str(payload or "").strip()
    digest = qr_payload_hash(text)
    next_hash: Optional[str] = None

    if in_flight:
        result = {
            "ok": False,
            "status": "submitting",
            "error": "簽到送出中，請稍候。",
            "payload_hash": digest,
            "qr_hash": digest,
        }
        result["view_state"] = build_qr_scan_view_state(submit_result=result, fanout=True)
        return sanitize_qr_scan_result(result), next_hash

    if not text:
        result = {
            "ok": False,
            "status": "empty_payload",
            "error": "沒有 QR 內容。",
        }
        result["view_state"] = build_qr_scan_view_state(submit_result=result, fanout=True)
        return sanitize_qr_scan_result(result), next_hash

    preview = _as_mapping(previewer(text)) if previewer is not None else {}
    if preview and not preview.get("ok"):
        preview["status"] = preview.get("status") or "parse_failed"
        preview["payload_hash"] = digest
        preview["qr_hash"] = digest
        preview["fanout"] = True
        preview["view_state"] = build_qr_scan_view_state(preview=preview, fanout=True)
        return sanitize_qr_scan_result(preview), next_hash

    account_list = list(accounts) if accounts is not None else []
    if not account_list:
        result = {
            "ok": False,
            "status": "no_accounts",
            "error": "簽到名單為空。",
            "payload_hash": digest,
            "qr_hash": digest,
            "results": [],
        }
        result["view_state"] = build_qr_scan_view_state(submit_result=result, fanout=True)
        return sanitize_qr_scan_result(result), next_hash

    if submitter is None:
        result = {
            "ok": False,
            "status": "failed",
            "error": "submitter_unavailable",
            "payload_hash": digest,
            "qr_hash": digest,
            "results": [],
        }
        result["view_state"] = build_qr_scan_view_state(submit_result=result, fanout=True)
        return sanitize_qr_scan_result(result), next_hash

    results: List[Dict[str, Any]] = []
    for profile in account_list:
        try:
            submitted = await _call_submitter(submitter, profile, text)
        except Exception as exc:
            submitted = {"ok": False, "status": "failed", "error": str(exc)}
        submitted["payload_hash"] = digest
        submitted["qr_hash"] = digest
        submitted.setdefault("profile", profile)
        if submitted.get("ok"):
            submitted.setdefault("status", "submitted")
        else:
            submitted.setdefault("status", "failed")
        results.append(submitted)

    ok = bool(results) and all(bool(item.get("ok")) for item in results)
    status = "submitted" if ok else "partial_failed"
    response: Dict[str, Any] = {
        "ok": ok,
        "status": status,
        "payload_hash": digest,
        "qr_hash": digest,
        "match_count": len(results),
        "results": results,
        "fanout": True,
    }
    if preview:
        response.setdefault("rollcall_id", preview.get("rollcall_id"))
        response.setdefault("provider", preview.get("provider"))
        response["preview"] = preview
    if ok:
        next_hash = digest
    response["view_state"] = build_qr_scan_view_state(
        preview=preview or None,
        submit_result=response,
        fanout=True,
    )
    return sanitize_qr_scan_result(response), next_hash


async def run_web_gui_qr_submit(
    payload: str,
    *,
    has_credentials: bool = False,
    last_success_hash: str = "",
    in_flight: bool = False,
    mode: str = "single",
    accounts: Optional[Sequence[str]] = None,
    submitter: Optional[Submitter] = None,
    previewer: Optional[Previewer] = None,
    fanout: bool = False,
    fanout_all: bool = False,
    **kwargs: Any,
) -> Tuple[Dict[str, Any], str]:
    if fanout or fanout_all:
        mode = "all"
    del kwargs
    mode = str(mode or "single").strip().lower()
    text = str(payload or "").strip()
    digest = qr_payload_hash(text)
    next_hash = last_success_hash or ""

    if mode == "all":
        result, multi_next = await run_multi_account_qr_submit(
            payload,
            accounts=accounts,
            in_flight=in_flight,
            submitter=submitter,
            previewer=previewer,
        )
        if multi_next:
            next_hash = multi_next
        return result, next_hash

    # single-account path (original behaviour)
    if in_flight:
        result = {
            "ok": False,
            "status": "submitting",
            "error": "簽到送出中，請稍候。",
            "payload_hash": digest,
            "qr_hash": digest,
        }
        result["view_state"] = build_qr_scan_view_state(submit_result=result, fanout=False)
        return sanitize_qr_scan_result(result), next_hash

    if not text:
        result = {
            "ok": False,
            "status": "empty_payload",
            "error": "沒有 QR 內容。",
        }
        result["view_state"] = build_qr_scan_view_state(submit_result=result, fanout=False)
        return sanitize_qr_scan_result(result), next_hash

    if not has_credentials:
        result = {
            "ok": False,
            "status": "missing_credentials",
            "error": "尚未設定帳號/學號與密碼，請至「帳號設定」填寫。",
            "payload_hash": digest,
            "qr_hash": digest,
        }
        result["view_state"] = build_qr_scan_view_state(submit_result=result, fanout=False)
        return sanitize_qr_scan_result(result), next_hash

    if digest and digest == last_success_hash:
        result = {
            "ok": True,
            "status": "already_submitted",
            "payload_hash": digest,
            "qr_hash": digest,
            "message": "此 QR 已用目前帳號送出過。",
        }
        result["view_state"] = build_qr_scan_view_state(submit_result=result, fanout=False)
        return sanitize_qr_scan_result(result), next_hash

    preview = _as_mapping(previewer(text)) if previewer is not None else {}
    if preview and not preview.get("ok"):
        preview["status"] = preview.get("status") or "parse_failed"
        preview["payload_hash"] = digest
        preview["qr_hash"] = digest
        preview["fanout"] = False
        preview["view_state"] = build_qr_scan_view_state(preview=preview, fanout=False)
        return sanitize_qr_scan_result(preview), next_hash

    if submitter is None:
        result = {
            "ok": False,
            "status": "failed",
            "error": "submitter_unavailable",
            "payload_hash": digest,
            "qr_hash": digest,
        }
        result["view_state"] = build_qr_scan_view_state(submit_result=result, fanout=False)
        return sanitize_qr_scan_result(result), next_hash

    submitted = _as_mapping(await _call_submitter(submitter, text))
    submitted["payload_hash"] = digest
    submitted["qr_hash"] = digest
    submitted["fanout"] = False
    if preview:
        submitted.setdefault("rollcall_id", preview.get("rollcall_id"))
        submitted.setdefault("provider", preview.get("provider"))
        submitted["preview"] = preview
    if submitted.get("ok"):
        next_hash = digest
        submitted.setdefault("status", "submitted")
    else:
        submitted.setdefault("status", "failed")
    submitted["view_state"] = build_qr_scan_view_state(
        preview=preview or None,
        submit_result=submitted,
        fanout=False,
    )
    return sanitize_qr_scan_result(submitted), next_hash