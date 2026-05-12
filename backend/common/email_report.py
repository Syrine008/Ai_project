"""Build HTML patient-facing report emails from AnalysisResult-shaped dicts."""
from __future__ import annotations

import html
import re
from typing import Any, Optional


def _strip_grad_cam(payload: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in payload.items() if k != "gradCamDataUrl"}
    return out


def _parse_metric_number(value: str) -> Optional[float]:
    if not value or not isinstance(value, str):
        return None
    m = re.search(r"[-+]?\d*\.?\d+", value.replace(",", "."))
    if not m:
        return None
    try:
        return float(m.group())
    except ValueError:
        return None


def _parse_brain_age_gap(metrics: list[Any]) -> Optional[float]:
    """Axis 4 exposes 'Brain–chronology Δ' (may use hyphen variants)."""
    for row in metrics:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "")
        ll = label.lower()
        if "chronology" in ll and ("Δ" in label or "\u0394" in label):
            return _parse_metric_number(str(row.get("value") or ""))
    for row in metrics:
        if not isinstance(row, dict):
            continue
        ll = str(row.get("label") or "").lower()
        if "brain" in ll and "chron" in ll:
            return _parse_metric_number(str(row.get("value") or ""))
    return None


def _parse_approx_range_high(metrics: list[Any]) -> Optional[float]:
    for row in metrics:
        if not isinstance(row, dict):
            continue
        if "approx" in str(row.get("label") or "").lower() and "range" in str(row.get("label") or "").lower():
            raw = str(row.get("value") or "")
            nums = re.findall(r"[-+]?\d*\.?\d+", raw.replace(",", "."))
            if len(nums) >= 2:
                try:
                    return max(float(nums[0]), float(nums[1]))
                except ValueError:
                    return None
    return None


def _parse_chronological_age_metric(metrics: list[Any]) -> Optional[float]:
    for row in metrics:
        if not isinstance(row, dict):
            continue
        lab = str(row.get("label") or "").lower()
        if "chronological" in lab and "age" in lab:
            return _parse_metric_number(str(row.get("value") or ""))
    return None


# Patient emails: show follow-up wording when estimate vs recorded age differs by more than this (years).
FOLLOW_UP_GAP_THRESHOLD_YEARS = 12


def should_include_follow_up_note(axis_id: str, result: dict[str, Any]) -> bool:
    """Large discrepancy vs chronological age → plain-language clinician note (Axis 4)."""
    if axis_id != "axis4-brain-aging":
        return False
    metrics = result.get("metrics") or []
    if not isinstance(metrics, list):
        return False
    thr = FOLLOW_UP_GAP_THRESHOLD_YEARS
    gap = _parse_brain_age_gap(metrics)
    if gap is not None and abs(gap) > thr:
        return True
    high = _parse_approx_range_high(metrics)
    chron = _parse_chronological_age_metric(metrics)
    if high is not None and chron is not None and (high - chron) > thr:
        return True
    return False


def _metrics_for_patient_email(axis_id: str, metrics: list[Any]) -> list[dict[str, Any]]:
    """Drop technical rows (MAE, etc.) and strip hints — patient-facing only."""
    out: list[dict[str, Any]] = []
    for m in metrics:
        if not isinstance(m, dict):
            continue
        lab = str(m.get("label") or "").lower()
        if axis_id == "axis4-brain-aging":
            if "mae" in lab or "typical error" in lab:
                continue
        row = dict(m)
        row.pop("hint", None)
        out.append(row)
    return out


def build_report_email_html(
    *,
    axis_title: str,
    patient_label: str,
    result: dict[str, Any],
    include_follow_up_note: bool,
    axis_id: str | None = None,
) -> str:
    """Structured HTML similar to on-screen report (no embedded Grad-CAM image)."""
    r = _strip_grad_cam(dict(result))
    case_id = html.escape(str(r.get("caseId") or "—"))
    gen = html.escape(str(r.get("generatedAt") or "—"))
    pred = html.escape(str(r.get("predictedClass") or "—"))
    summary = html.escape(str(r.get("summary") or "")).replace("\n", "<br/>")
    disclaimer = html.escape(str(r.get("disclaimer") or ""))

    resolved_axis_id = (axis_id or str(r.get("axisId") or "")).strip()

    follow_block = ""
    if include_follow_up_note:
        follow_block = """
        <div style="margin-top:18px;padding:14px 16px;background:#f4f9fb;border-radius:8px;border-left:4px solid #0d9488;">
          <p style="margin:0;font-size:14px;line-height:1.55;color:#134e4a;">
            <strong>For your safety and peace of mind:</strong> when the scan-based estimate and the age we have on file differ by more than about twelve years,
            we encourage you to mention this to your doctor. Automated tools can be affected by image quality and many normal differences between people.
            <strong>This does not mean you have a disease or that anything is wrong</strong> — it only means a clinician can put the numbers in the right context and advise you if any routine follow-up is appropriate.
          </p>
        </div>
        """

    metrics_rows = ""
    raw_metrics = r.get("metrics") or []
    metrics = (
        _metrics_for_patient_email(resolved_axis_id, raw_metrics)
        if isinstance(raw_metrics, list)
        else []
    )
    if metrics:
        rows = []
        for m in metrics:
            if not isinstance(m, dict):
                continue
            lab = html.escape(str(m.get("label") or ""))
            val = html.escape(str(m.get("value") or ""))
            rows.append(
                f"<tr><td style='padding:8px 12px;border-bottom:1px solid #e2e8f0;'>{lab}</td>"
                f"<td style='padding:8px 12px;border-bottom:1px solid #e2e8f0;'>{val}</td></tr>"
            )
        metrics_rows = (
            "<h3 style='margin:24px 0 8px;font-size:15px;color:#0f172a;'>Key numbers</h3>"
            "<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
            "<thead><tr style='background:#f8fafc;text-align:left;'>"
            "<th style='padding:8px 12px;'>Item</th><th style='padding:8px 12px;'>Value</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

    patient_safe = html.escape(patient_label or "Patient")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"></head>
<body style="font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#f8fafc;color:#0f172a;padding:24px;">
  <div style="max-width:640px;margin:0 auto;background:#ffffff;border-radius:12px;padding:28px;border:1px solid #e2e8f0;">
    <p style="margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:0.06em;color:#64748b;">Decision-support summary</p>
    <h1 style="margin:0 0 6px;font-size:20px;color:#0f172a;">{html.escape(axis_title)}</h1>
    <p style="margin:0 0 20px;font-size:14px;color:#475569;">Prepared for <strong>{patient_safe}</strong></p>
    <p style="margin:0 0 6px;font-size:13px;color:#64748b;">Case ID</p>
    <p style="margin:0 0 16px;font-size:15px;font-family:ui-monospace,monospace;">{case_id}</p>
    <p style="margin:0 0 6px;font-size:13px;color:#64748b;">Generated</p>
    <p style="margin:0 0 20px;font-size:14px;">{gen}</p>
    <h2 style="margin:0 0 10px;font-size:17px;color:#0f172a;">AI-assisted pattern</h2>
    <p style="margin:0 0 12px;font-size:16px;font-weight:600;color:#115e59;">{pred}</p>
    <p style="margin:0;font-size:14px;line-height:1.55;color:#334155;">{summary}</p>
    {follow_block}
    {metrics_rows}
    <div style="margin-top:28px;padding-top:18px;border-top:1px solid #e2e8f0;">
      <p style="margin:0;font-size:13px;line-height:1.55;color:#64748b;"><strong>Important:</strong> {disclaimer}</p>
      <p style="margin:12px 0 0;font-size:13px;line-height:1.55;color:#64748b;">
        This email was sent from the brAIn demo environment. Do not reply if you were not expecting clinical correspondence —
        contact your care team directly with questions.
      </p>
    </div>
    <p style="margin:20px 0 0;font-size:11px;color:#94a3b8;">Detailed figures are available from your clinician or the on-site report if needed.</p>
  </div>
</body></html>"""
