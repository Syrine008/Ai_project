import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from common.base import new_case_id

logger = logging.getLogger(__name__)


class AnalyzeView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from .ml.inference import MODEL_LOADER, ModelUnavailable, predict_path
        upload = request.FILES.get("file")
        try:
            metadata = json.loads(request.data.get("metadata", "{}"))
            if not isinstance(metadata, dict):
                raise ValueError()
        except (ValueError, TypeError):
            return Response({"detail": "metadata must be a JSON object."}, status=400)
        if upload is None:
            return Response({"detail": "Upload an MRI file. Cerebellum analysis does not use demo predictions."}, status=400)
        name = upload.name.lower()
        suffix = next((ext for ext in (".nii.gz", ".nii", ".npy") if name.endswith(ext)), None)
        if suffix is None or upload.size > 128 * 1024 * 1024:
            return Response({"detail": "Use a .nii, .nii.gz, or notebook .npy file up to 128 MB."}, status=400)
        input_space = metadata.get("inputSpace", "raw")
        if input_space not in ("raw", "mni", "notebook_crop"):
            return Response({"detail": "Unknown MRI input space."}, status=400)
        try:
            bundle = MODEL_LOADER.get()
            with TemporaryDirectory(prefix="cerebellum_") as directory:
                path = Path(directory) / ("scan" + suffix)
                with path.open("wb") as output:
                    for chunk in upload.chunks():
                        output.write(chunk)
                result = predict_path(path, input_space, bundle)
        except ModelUnavailable as exc:
            return Response({"detail": str(exc)}, status=503)
        except ImportError:
            return Response({"detail": "Cerebellum preprocessing dependencies are missing. Install requirements-cerebellum.txt."}, status=503)
        except (ValueError, OSError) as exc:
            return Response({"detail": f"Unable to read this MRI: {exc}"}, status=400)
        except Exception:
            logger.exception("Cerebellum inference failed")
            return Response({"detail": "Cerebellum analysis failed. Check the backend log."}, status=500)
        result["caseId"] = new_case_id()
        try:
            from common.models import Case, Result
            case = Case.objects.create(case_id=result["caseId"], axis_id=result["axisId"],
                                       file_name=upload.name, metadata=metadata)
            Result.objects.create(case=case, payload=result)
        except Exception:
            logger.warning("Could not persist cerebellum result", exc_info=True)
        return Response(result)
