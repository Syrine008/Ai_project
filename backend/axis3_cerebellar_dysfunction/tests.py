"""Contract tests use synthetic volumes/weights, never clinical performance claims.

Run from backend: python -m unittest axis3_cerebellar_dysfunction.tests -v
"""
import importlib.util
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile
from unittest.mock import patch
import nibabel as nib
import numpy as np
import torch

os.environ.setdefault("DJANGO_DEBUG", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brain_backend.settings")
import django
django.setup()
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory
from .ml.models import Fast3DCNN, SessionFast3DCNN, Strong3DCNN
from .ml.inference import CerebellumLoader, ModelUnavailable, predict_path, gradcam
from .ml.preprocessing import load_crop, stage_tensor
from .views import AnalyzeView
from .install_bundle import install

torch.set_num_threads(2)


class CerebellumTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rng = np.random.default_rng(12)

    def test_export_reload_and_prediction_parity(self):
        script = Path(__file__).resolve().parents[2] / "notebooks/export_cerebellum.py"
        spec = importlib.util.spec_from_file_location("cerebellum_export", script)
        exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exporter)
        first, second = Fast3DCNN(hidden=12).eval(), Strong3DCNN().eval()
        template = self.root / "template.nii.gz"
        nib.save(nib.Nifti1Image(np.ones((8, 8, 8)), np.eye(4)), template)
        archive = exporter.export_cerebellum({"model_fast": first, "model_ft": second, "MNI_PATH": template}, self.root / "bundle")
        install(archive, self.root / "installed")
        self.assertTrue((self.root / "installed/stage1.pth").is_file())
        restored = CerebellumLoader(self.root / "bundle").get()
        x = torch.from_numpy(self.rng.normal(size=(1, 1, 16, 16, 16)).astype(np.float32))
        with torch.no_grad():
            torch.testing.assert_close(first(x), restored[0](x))
            torch.testing.assert_close(second(x), restored[1](x))
        manifest_path = self.root / "bundle/manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["stage2_labels"].reverse()
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(ModelUnavailable):
            CerebellumLoader(self.root / "bundle").get()

    def test_installer_rejects_unexpected_archive_paths(self):
        archive = self.root / "invalid.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("../outside.txt", "unexpected")
        with self.assertRaises(ValueError):
            install(archive, self.root / "installed")
        self.assertFalse((self.root / "installed").exists())

    def test_missing_weights_fail_without_mock(self):
        with self.assertRaises(ModelUnavailable):
            CerebellumLoader(self.root).get()

    def test_session_stage1_export_reload(self):
        script = Path(__file__).resolve().parents[2] / "notebooks/export_cerebellum.py"
        spec = importlib.util.spec_from_file_location("session_export", script)
        exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exporter)
        first, second = SessionFast3DCNN().eval(), Strong3DCNN().eval()
        template = self.root / "template.nii.gz"
        nib.save(nib.Nifti1Image(np.ones((8, 8, 8)), np.eye(4)), template)
        exporter.export_cerebellum({"model_fast": first, "model_ft": second, "MNI_PATH": template}, self.root / "session")
        restored = CerebellumLoader(self.root / "session").get()
        self.assertIsInstance(restored[0], SessionFast3DCNN)
        x = torch.randn(1, 1, 16, 16, 16)
        with torch.no_grad():
            torch.testing.assert_close(first(x), restored[0](x))

    def test_crop_shape_finite_validation(self):
        path = self.root / "scan.npy"
        np.save(path, self.rng.random((128, 128, 64)).astype(np.float32))
        self.assertEqual(load_crop(path, "notebook_crop", self.root).shape, (128, 128, 64))
        for bad in [np.ones((16, 16, 16)), np.full((128, 128, 64), np.nan)]:
            np.save(path, bad)
            with self.assertRaises(ValueError):
                load_crop(path, "notebook_crop", self.root)

    def test_mni_grid_and_crop_match_notebook_math(self):
        volume = self.rng.random((160, 130, 100)).astype(np.float32)
        path, template = self.root / "scan.nii.gz", self.root / "mni.nii.gz"
        nib.save(nib.Nifti1Image(volume, np.eye(4)), path)
        nib.save(nib.Nifti1Image(np.zeros(volume.shape, dtype=np.float32), np.eye(4)), template)
        actual = load_crop(path, "mni", template)
        low, high = np.percentile(volume, [1, 99])
        expected = np.clip(volume, low, high)
        expected = (expected - expected.min()) / (expected.max() - expected.min() + 1e-8)
        expected = torch.nn.functional.interpolate(
            torch.tensor(expected[20:150, 20:120, 0:90].copy())[None, None],
            size=(128, 128, 64), mode="trilinear", align_corners=False)[0, 0].numpy()
        np.testing.assert_allclose(actual, expected)
        nib.save(nib.Nifti1Image(volume, np.diag([2, 2, 2, 1])), path)
        with self.assertRaises(ValueError):
            load_crop(path, "mni", template)

    def test_healthy_skips_second_model_and_anomaly_runs_it(self):
        first, second = Fast3DCNN().eval(), Strong3DCNN().eval()
        crop = self.rng.random((16, 16, 16)).astype(np.float32)
        with torch.no_grad():
            first.classifier[3].weight.zero_()
            first.classifier[3].bias.copy_(torch.tensor([5., -5.]))
            second.classifier[3].weight.zero_()
            second.classifier[3].bias.copy_(torch.tensor([-5., 5.]))
        with patch("axis3_cerebellar_dysfunction.ml.inference.load_crop", return_value=crop):
            with patch.object(second, "forward", wraps=second.forward) as forward:
                healthy = predict_path(self.root, "notebook_crop", (first, second, self.root))
                forward.assert_not_called()
            self.assertEqual(healthy["predictedClass"], "Healthy")
            self.assertIsNone(healthy["cerebellum"]["stage2"])
            with torch.no_grad():
                first.classifier[3].bias.copy_(torch.tensor([-5., 5.]))
            anomaly = predict_path(self.root, "notebook_crop", (first, second, self.root))
            self.assertEqual(anomaly["predictedClass"], "Cognitive anomaly")
            self.assertEqual(anomaly["cerebellum"]["explainabilityStage"], 2)
            self.assertTrue(anomaly["cerebellum"]["images"][0]["dataUrl"].startswith("data:image/png;base64,"))

    def test_gradcam_is_finite_and_removes_hooks(self):
        model = Fast3DCNN().eval()
        tensor = stage_tensor(self.rng.random((16, 16, 16)).astype(np.float32), strip=False)
        result = gradcam(model, tensor, 0)
        self.assertEqual(len(result["images"]), 2)
        self.assertFalse(model.features[4]._forward_hooks)

    def request(self, metadata="{}", name="scan.npy"):
        content = io.BytesIO()
        np.save(content, self.rng.random((128, 128, 64)).astype(np.float32))
        upload = SimpleUploadedFile(name, content.getvalue())
        request = APIRequestFactory().post("/api/axis3-cerebellar-dysfunction/analyze/",
                                          {"file": upload, "metadata": metadata}, format="multipart")
        return AnalyzeView.as_view()(request)

    def test_api_validation_and_missing_models(self):
        for metadata, name in [("[]", "scan.npy"), ("invalid", "scan.npy"), ("{}", "scan.dcm")]:
            self.assertEqual(self.request(metadata, name).status_code, 400)
        with patch("axis3_cerebellar_dysfunction.ml.inference.MODEL_LOADER", CerebellumLoader(self.root)):
            response = self.request()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("predictedClass", response.data)

    def test_api_success_saves_and_cleans_upload(self):
        observed = []
        def predict(path, space, bundle):
            self.assertTrue(path.is_file())
            self.assertEqual(space, "notebook_crop")
            observed.append(path)
            return {"axisId": "axis3-cerebellar-dysfunction", "modelLoaded": True}
        with patch("axis3_cerebellar_dysfunction.ml.inference.MODEL_LOADER.get", return_value=object()), \
             patch("axis3_cerebellar_dysfunction.ml.inference.predict_path", side_effect=predict), \
             patch("common.models.Case.objects.create"), patch("common.models.Result.objects.create"):
            response = self.request('{"inputSpace":"notebook_crop"}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["caseId"].startswith("BRN-"))
        self.assertFalse(observed[0].exists())


if __name__ == "__main__":
    unittest.main()
