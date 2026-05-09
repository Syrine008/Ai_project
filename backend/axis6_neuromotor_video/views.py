from common.base import AxisConfig, BaseAnalyzeView
from .ml.inference import MODEL_LOADER, predict


class AnalyzeView(BaseAnalyzeView):
    axis_config = AxisConfig(
        axis_id="axis6-neuromotor-video",
        predict=predict,
        loader=MODEL_LOADER,
        accepted_extensions=('.mp4', '.mov', '.webm'),
    )
