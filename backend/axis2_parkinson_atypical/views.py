from common.base import AxisConfig, BaseAnalyzeView
from .ml.inference import MODEL_LOADER, predict


class AnalyzeView(BaseAnalyzeView):
    axis_config = AxisConfig(
        axis_id="axis2-parkinson-atypical",
        predict=predict,
        loader=MODEL_LOADER,
        accepted_extensions=('.nii', '.nii.gz', '.dcm'),
    )
