from common.base import AxisConfig, BaseAnalyzeView
from .ml.inference import MODEL_LOADER, predict


class AnalyzeView(BaseAnalyzeView):
    axis_config = AxisConfig(
        axis_id="axis1-alzheimer-dementia",
        predict=predict,
        loader=MODEL_LOADER,
        accepted_extensions=('.nii', '.nii.gz', '.dcm'),
    )
