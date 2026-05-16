from common.base import AxisConfig, BaseAnalyzeView


class AnalyzeView(BaseAnalyzeView):
    def get_axis_config(self) -> AxisConfig:
        from .ml.inference import MODEL_LOADER, predict

        return AxisConfig(
            axis_id="axis2-parkinson-atypical",
            predict=predict,
            loader=MODEL_LOADER,
            accepted_extensions=('.nii', '.nii.gz', '.dcm'),
        )
