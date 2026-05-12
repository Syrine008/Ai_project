"""Cross-cutting API views (report email, etc.)."""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .email_report import build_report_email_html, should_include_follow_up_note

logger = logging.getLogger(__name__)


class SendReportEmailView(APIView):
    """POST JSON body to email an HTML summary to the patient (SMTP configurable)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            return self._post_impl(request, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — never return bare Django HTML 500 to the SPA
            logger.exception("send-report-email failed")
            return Response(
                {"detail": f"Email handler error: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _post_impl(self, request, *args, **kwargs):
        to_addr = (request.data.get("to") or "").strip()
        axis_id = (request.data.get("axis_id") or "").strip()
        axis_title = (request.data.get("axis_title") or axis_id or "Analysis").strip()
        patient = request.data.get("patient") or {}
        result = request.data.get("result")

        if not to_addr:
            return Response({"detail": "`to` (recipient email) is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_email(to_addr)
        except ValidationError:
            return Response({"detail": "Invalid email address."}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(result, dict):
            return Response({"detail": "`result` must be the AnalysisResult object."}, status=status.HTTP_400_BAD_REQUEST)

        pid = ""
        if isinstance(patient, dict):
            pid = str(patient.get("id") or "").strip()
        patient_label = pid or "Patient"

        include_note = should_include_follow_up_note(axis_id, result)
        html_body = build_report_email_html(
            axis_title=axis_title,
            patient_label=patient_label,
            result=result,
            include_follow_up_note=include_note,
            axis_id=axis_id,
        )

        case_id = str(result.get("caseId") or "report")
        subject = f"[brAIn] Analysis summary — {axis_title} ({case_id})"

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "webmaster@localhost"

        msg = EmailMultiAlternatives(
            subject=subject,
            body="This message contains HTML. Use an HTML-capable mail client.",
            from_email=from_email,
            to=[to_addr],
        )
        msg.attach_alternative(html_body, "text/html")

        try:
            msg.send(fail_silently=False)
        except Exception as exc:  # noqa: BLE001 — surface SMTP errors to the UI in dev
            return Response(
                {"detail": f"Could not send email: {exc}", "hint": "Check EMAIL_* settings and SMTP credentials."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"ok": True, "to": to_addr, "followUpNote": include_note}, status=status.HTTP_200_OK)
