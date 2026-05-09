from common.base import AxisConfig, BaseAnalyzeView
from .ml.inference import MODEL_LOADER, predict


class AnalyzeView(BaseAnalyzeView):
    axis_config = AxisConfig(
        axis_id="axis7-epilepsy-network",
        predict=predict,
        loader=MODEL_LOADER,
        accepted_extensions=('.edf', '.bdf', '.csv'),
    )
