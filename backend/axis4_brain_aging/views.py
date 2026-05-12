"""Axis 4 accepts optional second multipart field ``file_analyze_pair`` for Analyze .hdr+.img."""
from __future__ import annotations

import json

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.base import AxisConfig, new_case_id

from .ml.inference import MODEL_LOADER, predict


class AnalyzeView(APIView):
    """Same contract as ``BaseAnalyzeView`` plus optional Analyze companion upload."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    axis_config = AxisConfig(
        axis_id="axis4-brain-aging",
        predict=predict,
        loader=MODEL_LOADER,
        accepted_extensions=(
            ".nii",
            ".nii.gz",
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".zip",
            ".hdr",
            ".img",
            ".HDR",
            ".IMG",
        ),
    )

    def post(self, request, *args, **kwargs):
        cfg = self.axis_config

        upload = request.FILES.get("file")
        pair_upload = request.FILES.get("file_analyze_pair")
        metadata_raw = request.data.get("metadata", "{}")
        if isinstance(metadata_raw, str):
            try:
                metadata = json.loads(metadata_raw or "{}")
            except json.JSONDecodeError:
                return Response(
                    {"detail": "metadata must be valid JSON"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            metadata = dict(metadata_raw)

        if upload is None and not metadata.get("demo"):
            return Response(
                {"detail": "file is required (or set metadata.demo=true)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if upload and cfg.accepted_extensions:
            name = (upload.name or "").lower()
            if not any(name.endswith(ext.lower()) for ext in cfg.accepted_extensions):
                return Response(
                    {
                        "detail": (
                            f"Unsupported file type for {cfg.axis_id}. "
                            f"Accepted: {', '.join(cfg.accepted_extensions)}"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        merged_meta = dict(metadata)
        if pair_upload is not None:
            merged_meta["_internal_analyze_pair_bytes"] = pair_upload.read()
            merged_meta["_internal_analyze_pair_name"] = pair_upload.name or ""

        case_id = new_case_id()
        model = cfg.loader.get()
        result = predict(upload, model, merged_meta)

        persist_meta = {
            k: v for k, v in merged_meta.items() if not str(k).startswith("_internal_")
        }

        result.setdefault("axisId", cfg.axis_id)
        result["caseId"] = case_id
        result.setdefault(
            "disclaimer",
            "Decision-support tool. Not a medical diagnosis. "
            "Clinical correlation required.",
        )
        result["modelLoaded"] = cfg.loader.is_available

        try:
            from common.models import Case, Result

            case = Case.objects.create(
                case_id=case_id,
                axis_id=cfg.axis_id,
                file_name=getattr(upload, "name", "") or "",
                metadata=persist_meta,
            )
            Result.objects.create(case=case, payload=result)
        except Exception:  # pragma: no cover
            pass

        return Response(result, status=status.HTTP_200_OK)
