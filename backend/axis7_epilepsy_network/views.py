import json

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.base import AxisConfig, new_case_id


class AnalyzeView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_axis_config(self) -> AxisConfig:
        from .ml.inference import MODEL_LOADER, predict

        return AxisConfig(
            axis_id="axis7-epilepsy-network",
            predict=predict,
            loader=MODEL_LOADER,
            accepted_extensions=(".edf", ".bdf", ".csv", ".json", ".tsv", ".zip", ".nii", ".nii.gz"),
        )

    def post(self, request, *args, **kwargs):
        cfg = self.get_axis_config()
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

        folder_files = request.FILES.getlist("files")
        upload = folder_files or request.FILES.get("file")
        if upload is None and not metadata.get("demo") and not metadata.get("localFolderPath"):
            return Response(
                {"detail": "folder files or metadata.localFolderPath are required (or set metadata.demo=true)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        files_to_check = folder_files if folder_files else ([upload] if upload else [])
        for item in files_to_check:
            name = (getattr(item, "name", "") or "").lower()
            if name and not any(name.endswith(ext) for ext in cfg.accepted_extensions):
                return Response(
                    {
                        "detail": (
                            f"Unsupported file type for {cfg.axis_id}. "
                            f"Accepted: {', '.join(cfg.accepted_extensions)}"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        case_id = new_case_id()
        model = cfg.loader.get()
        result = cfg.predict(upload, model, metadata)

        result.setdefault("axisId", cfg.axis_id)
        result["caseId"] = case_id
        result.setdefault(
            "disclaimer",
            "Decision-support tool. Not a medical diagnosis. Clinical correlation required.",
        )
        result["modelLoaded"] = cfg.loader.is_available

        try:
            from common.models import Case, Result

            first_file = files_to_check[0] if files_to_check else None
            case = Case.objects.create(
                case_id=case_id,
                axis_id=cfg.axis_id,
                file_name=getattr(first_file, "name", "") or "",
                metadata={
                    **metadata,
                    "folderFileCount": len(folder_files),
                },
            )
            Result.objects.create(case=case, payload=result)
        except Exception:
            pass

        return Response(result, status=status.HTTP_200_OK)
