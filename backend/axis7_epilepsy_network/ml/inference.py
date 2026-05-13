from __future__ import annotations

import csv
import base64
import io
import json
import os
import re
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch

from ..explain.explainer import build_network, build_regions, build_signal, build_timeline
from .architecture import build_model_from_artifact

TORCH_ARTIFACT_PATH = Path(__file__).resolve().parent / "axis7_epilepsy_network_model.pt"
LEGACY_MODEL_PATH = Path(__file__).resolve().parent / "axis7_epilepsy_network_model.pkl"
DEFAULT_SAMPLE_RATE = 256.0
DEFAULT_WINDOW_SEC = 10.0
PROJECT_ROOT = Path(__file__).resolve().parents[4]
FMRI_PATH = PROJECT_ROOT / "ds007313" / "derivatives" / "denoising" / "slice_wise" / "2_func_in_template" / "brain" / "sub-A006_task-rest_bold_stc_brain_moco_BP_nostd_inT1w_inTemplate.nii.gz"
NOTEBOOK_VENV_SITE = PROJECT_ROOT / "venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
MOV_SENSOR_PREFIX = "EEG SD ACC"
CLASSES = [
    "Low vulnerability",
    "Moderate instability",
    "High vulnerability",
]
UPLOAD_SIGNAL_EXTENSIONS = {".edf", ".bdf"}
UPLOAD_METADATA_EXTENSIONS = {".csv", ".json", ".tsv", ".nii", ".gz"}


def _is_nifti_name(name: str) -> bool:
    lowered = name.lower()
    return lowered.endswith(".nii") or lowered.endswith(".nii.gz")


def _is_supported_upload_name(name: str) -> bool:
    lowered = name.lower()
    suffix = Path(lowered).suffix
    return suffix in UPLOAD_SIGNAL_EXTENSIONS | UPLOAD_METADATA_EXTENSIONS or _is_nifti_name(lowered) or lowered.endswith(".zip")


@dataclass
class LoadedAxis7Model:
    kind: str
    label: str
    model: Any
    artifact: dict[str, Any]


@dataclass
class UploadBundle:
    source_name: str
    sample_rate: float
    duration_sec: float
    modality_sample_rates: dict[str, float]
    eeg: np.ndarray
    ecg: np.ndarray
    emg: np.ndarray
    mov: np.ndarray
    eeg_channel_names: list[str]
    display_channel_names: list[str]
    display_matrix: np.ndarray
    primary_signal: np.ndarray
    subject_id: str | None = None
    session_id: str | None = None
    run_id: str | None = None
    metadata_summary: dict[str, Any] | None = None


def _import_mne():
    try:
        import mne

        return mne
    except ModuleNotFoundError:
        if NOTEBOOK_VENV_SITE.exists():
            site_path = str(NOTEBOOK_VENV_SITE)
            if site_path not in sys.path:
                sys.path.append(site_path)
        import mne

        return mne


def _ensure_notebook_site_path() -> None:
    if NOTEBOOK_VENV_SITE.exists():
        site_path = str(NOTEBOOK_VENV_SITE)
        if site_path not in sys.path:
            sys.path.append(site_path)


def _import_matplotlib_pyplot():
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    _ensure_notebook_site_path()
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


class Axis7ModelLoader:
    def __init__(self, torch_path: Path, legacy_path: Path) -> None:
        self.torch_path = torch_path
        self.legacy_path = legacy_path
        self._model: Optional[LoadedAxis7Model] = None
        self._stamp: tuple[float, float] | None = None

    def _current_stamp(self) -> tuple[float, float]:
        torch_mtime = self.torch_path.stat().st_mtime if self.torch_path.exists() else -1.0
        legacy_mtime = self.legacy_path.stat().st_mtime if self.legacy_path.exists() else -1.0
        return (torch_mtime, legacy_mtime)

    def get(self) -> Optional[LoadedAxis7Model]:
        stamp = self._current_stamp()
        if self._stamp == stamp and self._model is not None:
            return self._model
        if self._stamp == stamp:
            return None
        self._stamp = stamp
        self._model = None

        if self.torch_path.exists():
            try:
                artifact = torch.load(self.torch_path, map_location="cpu", weights_only=False)
                model = build_model_from_artifact(artifact)
                self._model = LoadedAxis7Model(
                    kind="torch",
                    label=str(artifact.get("model_name") or artifact.get("model_class") or "Notebook CNN"),
                    model=model,
                    artifact=artifact,
                )
                return self._model
            except Exception:
                self._model = None

        if self.legacy_path.exists():
            try:
                import joblib

                legacy_model = joblib.load(self.legacy_path)
                self._model = LoadedAxis7Model(
                    kind="joblib",
                    label="Legacy model",
                    model=legacy_model,
                    artifact={},
                )
                return self._model
            except Exception:
                self._model = None

        return None

    @property
    def is_available(self) -> bool:
        return self.get() is not None


MODEL_LOADER = Axis7ModelLoader(TORCH_ARTIFACT_PATH, LEGACY_MODEL_PATH)


def _to_float_array(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float32)
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    return arr


def _normalize_channelwise(arr: np.ndarray) -> np.ndarray:
    arr = _to_float_array(arr)
    mean = arr.mean(axis=1, keepdims=True)
    std = arr.std(axis=1, keepdims=True) + 1e-6
    return (arr - mean) / std


def _resample_channels(arr: np.ndarray, target_len: int) -> np.ndarray:
    arr = _to_float_array(arr)
    if arr.shape[1] == target_len:
        return arr.astype(np.float32)
    if arr.shape[1] <= 1:
        return np.repeat(arr[:, :1], target_len, axis=1).astype(np.float32)

    source_x = np.linspace(0.0, 1.0, arr.shape[1], endpoint=False)
    target_x = np.linspace(0.0, 1.0, target_len, endpoint=False)
    resampled = [np.interp(target_x, source_x, channel).astype(np.float32) for channel in arr]
    return np.stack(resampled, axis=0)


def _pad_or_trim_channels(arr: np.ndarray, target_channels: int) -> np.ndarray:
    arr = _to_float_array(arr)
    if arr.shape[0] == target_channels:
        return arr
    if arr.shape[0] == 0:
        return np.zeros((target_channels, arr.shape[1]), dtype=np.float32)
    if arr.shape[0] > target_channels:
        return arr[:target_channels]

    out = np.zeros((target_channels, arr.shape[1]), dtype=np.float32)
    out[: arr.shape[0]] = arr
    if arr.shape[0] == 1 and target_channels >= 2:
        out[1] = arr[0]
    return out


def _extract_window(arr: np.ndarray, start: int, length: int) -> np.ndarray:
    if arr.shape[1] == 0:
        return np.zeros((arr.shape[0], length), dtype=np.float32)
    window = arr[:, start : start + length]
    if window.shape[1] == length:
        return window.astype(np.float32)
    if window.shape[1] == 0:
        pad = np.zeros((arr.shape[0], length), dtype=np.float32)
        return pad
    pad_width = length - window.shape[1]
    return np.pad(window, ((0, 0), (0, pad_width)), mode="edge").astype(np.float32)


def _window_starts(total_samples: int, window_len: int, step_len: int) -> list[int]:
    if total_samples <= window_len:
        return [0]
    starts = list(range(0, max(total_samples - window_len + 1, 1), step_len))
    last_start = total_samples - window_len
    if not starts or starts[-1] != last_start:
        starts.append(last_start)
    return starts


def _score_to_confidence(probability: float) -> list[dict[str, Any]]:
    high = float(np.clip(probability, 0.0, 1.0))
    low = float(np.clip(1.0 - probability, 0.0, 1.0))
    moderate = float(max(0.0, 1.0 - abs(probability - 0.5) * 2.0) * 0.7)
    total = max(high + low + moderate, 1e-6)
    values = [low / total, moderate / total, high / total]
    return [
        {"label": CLASSES[index], "value": round(float(value), 4)}
        for index, value in enumerate(values)
    ]


def _predicted_class(probability: float) -> str:
    if probability >= 0.7:
        return "High vulnerability pattern detected"
    if probability >= 0.45:
        return "Moderate instability pattern detected"
    return "Relatively stable background pattern"


def _sniff_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t ")
        return dialect.delimiter
    except Exception:
        return ","


def _is_float_token(token: str) -> bool:
    try:
        float(token)
        return True
    except Exception:
        return False


def _load_csv_matrix(upload) -> tuple[np.ndarray, list[str], float]:
    raw_bytes = upload.read()
    text = raw_bytes.decode("utf-8-sig", errors="ignore")
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("CSV upload is empty.")

    delimiter = _sniff_delimiter("\n".join(lines[:5]))
    first_tokens = [token.strip() for token in lines[0].split(delimiter)]
    has_header = not all(_is_float_token(token) for token in first_tokens)

    reader = csv.reader(lines[1:] if has_header else lines, delimiter=delimiter)
    rows = []
    for row in reader:
        numeric = []
        for token in row:
            token = token.strip()
            if token == "":
                continue
            try:
                numeric.append(float(token))
            except ValueError:
                numeric = []
                break
        if numeric:
            rows.append(numeric)

    if not rows:
        raise ValueError("CSV upload does not contain numeric signal rows.")

    width = min(len(row) for row in rows)
    matrix = np.asarray([row[:width] for row in rows], dtype=np.float32)
    if matrix.ndim != 2:
        raise ValueError("CSV upload could not be parsed into a 2D matrix.")

    headers = [token.strip() for token in first_tokens[:width]] if has_header else []
    if headers and headers[0].lower() in {"time", "timestamp", "t", "sec", "seconds"} and width > 1:
        matrix = matrix[:, 1:]
        headers = headers[1:]

    channel_names = headers if headers else [f"Signal {index + 1}" for index in range(matrix.shape[1])]
    return matrix.T.astype(np.float32), channel_names, DEFAULT_SAMPLE_RATE


def _load_edf_like_matrix(upload) -> tuple[np.ndarray, list[str], list[str], float]:
    suffix = Path(getattr(upload, "name", "signal.edf")).suffix.lower() or ".edf"
    raw_bytes = upload.read()
    fd, temp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        with open(temp_path, "wb") as handle:
            handle.write(raw_bytes)

        mne = _import_mne()

        if suffix == ".bdf":
            raw = mne.io.read_raw_bdf(temp_path, preload=True, verbose="ERROR")
        else:
            raw = mne.io.read_raw_edf(temp_path, preload=True, verbose="ERROR")

        matrix = raw.get_data().astype(np.float32)
        channel_names = list(raw.ch_names)
        channel_types = list(raw.get_channel_types())
        sample_rate = float(raw.info.get("sfreq") or DEFAULT_SAMPLE_RATE)
        return matrix, channel_names, channel_types, sample_rate
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def _load_raw_from_path(path: Path, max_duration_sec: float | None = None):
    mne = _import_mne()
    suffix = path.suffix.lower()
    if suffix == ".bdf":
        raw = mne.io.read_raw_bdf(str(path), preload=False, verbose="ERROR")
    else:
        raw = mne.io.read_raw_edf(str(path), preload=False, verbose="ERROR")

    if max_duration_sec is not None:
        max_time = max(float(max_duration_sec), 1.0)
        if raw.times.size and raw.times[-1] > max_time:
            raw.crop(tmin=0.0, tmax=max_time, include_tmax=False)

    raw.load_data(verbose="ERROR")
    return raw


def _pick_indices(
    channel_names: list[str],
    channel_types: list[str],
    *,
    preferred_names: list[str] | None = None,
    preferred_type: str | None = None,
    keywords: list[str] | None = None,
    count: int,
) -> list[int]:
    preferred_names = preferred_names or []
    keywords = [keyword.lower() for keyword in (keywords or [])]
    lowered_names = [name.lower() for name in channel_names]

    picks: list[int] = []
    for preferred in preferred_names:
        preferred_lower = str(preferred).lower()
        for index, name in enumerate(lowered_names):
            if name == preferred_lower or name.endswith(preferred_lower):
                if index not in picks:
                    picks.append(index)
                break

    if preferred_type:
        for index, channel_type in enumerate(channel_types):
            if len(picks) >= count:
                break
            if channel_type == preferred_type and index not in picks:
                picks.append(index)

    if keywords:
        for index, name in enumerate(lowered_names):
            if len(picks) >= count:
                break
            if any(keyword in name for keyword in keywords) and index not in picks:
                picks.append(index)

    for index in range(len(channel_names)):
        if len(picks) >= count:
            break
        if index not in picks:
            picks.append(index)

    return picks[:count]


def _select_display_channels(channel_names: list[str], matrix: np.ndarray) -> tuple[list[str], np.ndarray]:
    if matrix.shape[0] <= 6:
        return channel_names, matrix
    scores = matrix.std(axis=1)
    order = np.argsort(scores)[::-1][:6]
    selected_names = [channel_names[index] for index in order]
    return selected_names, matrix[order]


def _parse_identity(text: str) -> tuple[str | None, str | None, str | None]:
    subject_match = re.search(r"(sub-[A-Za-z0-9]+)", text)
    session_match = re.search(r"(ses-[A-Za-z0-9]+)", text)
    run_match = re.search(r"run-([A-Za-z0-9]+)", text)
    subject_id = subject_match.group(1) if subject_match else None
    session_id = session_match.group(1) if session_match else None
    run_id = f"run-{run_match.group(1)}" if run_match else None
    return subject_id, session_id, run_id


def _pick_mov_channels_from_names(channel_names: list[str]) -> list[int]:
    preferred = [idx for idx, name in enumerate(channel_names) if name.startswith(MOV_SENSOR_PREFIX)]
    if len(preferred) >= 3:
        return preferred[:3]
    acc = [idx for idx, name in enumerate(channel_names) if "ACC" in name.upper()]
    if len(acc) >= 3:
        return acc[:3]
    return list(range(min(3, len(channel_names))))


def _event_is_seizure(label: str) -> bool:
    value = str(label or "").strip().lower()
    if not value or value in {"n/a", "na", "none", "background", "impd"}:
        return False
    return any(token in value for token in ["seiz", "sz", "ictal", "onset"])


def _metadata_summary_from_paths(paths: list[Path], metadata: dict[str, Any]) -> dict[str, Any]:
    source_names = [path.as_posix() for path in paths]
    identity_source = " ".join(source_names)
    subject_id, session_id, run_id = _parse_identity(identity_source)
    summary: dict[str, Any] = {
        "source_names": source_names,
        "subject_id": metadata.get("subjectId") or metadata.get("patientId") or subject_id,
        "session_id": metadata.get("session") or session_id,
        "run_id": metadata.get("run") or run_id,
        "sample_rate": DEFAULT_SAMPLE_RATE,
        "recording_duration": None,
        "events": [],
        "seizure_events": [],
        "excluded_events": [],
    }

    for path in paths:
        suffix = path.suffix.lower()
        name = path.name.lower()
        try:
            if suffix == ".json":
                payload = json.loads(path.read_text(errors="ignore") or "{}")
                if payload.get("SamplingFrequency"):
                    summary["sample_rate"] = float(payload["SamplingFrequency"])
                if payload.get("RecordingDuration"):
                    summary["recording_duration"] = float(payload["RecordingDuration"])
            elif suffix == ".tsv" or name.endswith("_events.tsv"):
                text = path.read_text(errors="ignore")
                reader = csv.DictReader(io.StringIO(text), delimiter="\t")
                for row in reader:
                    label = row.get("eventType") or row.get("trial_type") or row.get("event_type") or row.get("type") or ""
                    try:
                        onset = float(row.get("onset") or 0.0)
                    except Exception:
                        onset = 0.0
                    try:
                        duration = float(row.get("duration") or 0.0)
                    except Exception:
                        duration = 0.0
                    event = {
                        "onset": onset,
                        "duration": duration,
                        "label": str(label or "event"),
                        "localization": row.get("localization") or "n/a",
                        "lateralization": row.get("lateralization") or "n/a",
                    }
                    summary["events"].append(event)
                    if str(label).strip().lower() == "impd":
                        summary["excluded_events"].append(event)
                    if _event_is_seizure(str(label)):
                        summary["seizure_events"].append(event)
        except Exception:
            continue

    if summary["recording_duration"] is None and summary["events"]:
        summary["recording_duration"] = max(event["onset"] + event["duration"] for event in summary["events"])

    return summary


def _build_metadata_bundle_from_paths(paths: list[Path], metadata: dict[str, Any]) -> UploadBundle:
    summary = _metadata_summary_from_paths(paths, metadata)
    original_duration = float(summary.get("recording_duration") or 300.0)
    duration_sec = float(np.clip(original_duration if np.isfinite(original_duration) else 300.0, 120.0, 900.0))
    sample_rate = 64.0
    samples = max(1, int(round(duration_sec * sample_rate)))
    time = np.linspace(0.0, duration_sec, samples, endpoint=False)

    eeg_left = 0.08 * np.sin(time * 2.1) + 0.03 * np.sin(time * 15.0)
    eeg_right = 0.07 * np.sin(time * 1.8 + 0.3) + 0.025 * np.sin(time * 13.0)
    ecg = 0.12 * np.sin(time * 1.2)
    emg = 0.04 * np.sin(time * 8.0)
    mov = np.stack(
        [
            0.03 * np.sin(time * 0.9),
            0.025 * np.sin(time * 1.2 + 0.5),
            0.02 * np.sin(time * 0.7 + 1.1),
        ]
    )

    scale = duration_sec / max(original_duration, duration_sec, 1.0)
    for event in summary.get("seizure_events", []):
        onset = float(event["onset"]) * scale
        width = max(float(event["duration"]) * scale, 2.0)
        mask = (time >= onset) & (time <= onset + width)
        if mask.any():
            burst_time = time[mask] - onset
            eeg_left[mask] += 1.1 * np.sin(burst_time * 22.0)
            eeg_right[mask] += 0.9 * np.sin(burst_time * 18.0)
            emg[mask] += 0.15 * np.sin(burst_time * 10.0)

    eeg = np.stack([eeg_left, eeg_right]).astype(np.float32)
    ecg_arr = ecg.reshape(1, -1).astype(np.float32)
    emg_arr = emg.reshape(1, -1).astype(np.float32)
    mov_arr = mov.astype(np.float32)
    display_matrix = np.concatenate([eeg, ecg_arr, emg_arr, mov_arr], axis=0)

    return UploadBundle(
        source_name="BIDS metadata upload",
        sample_rate=sample_rate,
        duration_sec=duration_sec,
        modality_sample_rates={"eeg": sample_rate, "ecg": sample_rate, "emg": sample_rate, "mov": sample_rate},
        eeg=eeg,
        ecg=ecg_arr,
        emg=emg_arr,
        mov=mov_arr,
        eeg_channel_names=["BTEleft SD", "CROSStop SD"],
        display_channel_names=["BTEleft SD", "CROSStop SD", "ECG", "EMG", "ACC X", "ACC Y", "ACC Z"],
        display_matrix=display_matrix,
        primary_signal=eeg.mean(axis=0).astype(np.float32),
        subject_id=summary.get("subject_id"),
        session_id=summary.get("session_id"),
        run_id=summary.get("run_id"),
        metadata_summary=summary,
    )


def _load_multimodal_path_bundle(
    folder_path: Path,
    source_name: str,
    artifact: dict[str, Any] | None,
    metadata: dict[str, Any],
) -> UploadBundle:
    if not folder_path.exists() or not folder_path.is_dir():
        raise ValueError(f"Local folder does not exist: {folder_path}")

    preferred_eeg_names = list(artifact.get("eeg_channel_names", [])) if artifact else []
    meta_subject = metadata.get("subjectId") or metadata.get("patientId")
    meta_session = metadata.get("session")
    meta_run = metadata.get("run")

    all_signal_files = [
        path
        for path in folder_path.rglob("*")
        if path.is_file() and path.suffix.lower() in {".edf", ".bdf"}
    ]
    if not all_signal_files:
        raise ValueError(f"Local folder did not contain EDF/BDF files: {folder_path}")

    grouped: dict[tuple[str | None, str | None, str | None], dict[str, Path]] = {}
    for path in all_signal_files:
        subject_id, session_id, run_id = _parse_identity(path.name)
        lower_name = path.name.lower()
        modality = None
        for candidate in ["eeg", "ecg", "emg", "mov"]:
            if f"_{candidate}." in lower_name or lower_name.endswith(f"{candidate}{path.suffix.lower()}"):
                modality = candidate
                break
        if modality is None:
            continue
        key = (subject_id, session_id, run_id)
        grouped.setdefault(key, {})[modality] = path

    chosen_key = None
    chosen_files = None
    requested_run = meta_run if str(meta_run or "").startswith("run-") else (f"run-{meta_run}" if meta_run else None)
    for key, files in grouped.items():
        if not {"eeg", "ecg", "emg", "mov"}.issubset(files):
            continue
        subject_id, session_id, run_id = key
        if meta_subject and subject_id and meta_subject != subject_id:
            continue
        if meta_session and session_id and meta_session != session_id:
            continue
        if requested_run and run_id and requested_run != run_id:
            continue
        chosen_key = key
        chosen_files = files
        break

    if chosen_files is None:
        for key, files in grouped.items():
            if {"eeg", "ecg", "emg", "mov"}.issubset(files):
                chosen_key = key
                chosen_files = files
                break

    if chosen_files is None:
        raise ValueError(
            "Folder must contain one complete patient run with matching eeg/ecg/emg/mov EDF files."
        )

    max_read_seconds = float(metadata.get("maxReadSeconds") or 300.0)
    eeg_raw = _load_raw_from_path(chosen_files["eeg"], max_read_seconds)
    ecg_raw = _load_raw_from_path(chosen_files["ecg"], max_read_seconds)
    emg_raw = _load_raw_from_path(chosen_files["emg"], max_read_seconds)
    mov_raw = _load_raw_from_path(chosen_files["mov"], max_read_seconds)

    eeg_names = list(eeg_raw.ch_names)
    eeg_types = list(eeg_raw.get_channel_types())
    eeg_idx = _pick_indices(
        eeg_names,
        eeg_types,
        preferred_names=preferred_eeg_names,
        preferred_type="eeg",
        keywords=["bteleft", "crosstop", "bteright", "eeg"],
        count=2,
    )
    ecg = _pad_or_trim_channels(ecg_raw.get_data(), 1)
    emg = _pad_or_trim_channels(emg_raw.get_data(), 1)
    mov_idx = _pick_mov_channels_from_names(list(mov_raw.ch_names))
    mov = _pad_or_trim_channels(mov_raw.get_data(picks=mov_idx), 3)
    eeg = _pad_or_trim_channels(eeg_raw.get_data(picks=eeg_idx), 2)
    eeg_channel_names = [eeg_names[index] for index in eeg_idx[:2]]
    if len(eeg_channel_names) == 1:
        eeg_channel_names.append(f"{eeg_channel_names[0]} (dup)")

    eeg_rate = float(eeg_raw.info.get("sfreq") or DEFAULT_SAMPLE_RATE)
    ecg_rate = float(ecg_raw.info.get("sfreq") or eeg_rate)
    emg_rate = float(emg_raw.info.get("sfreq") or eeg_rate)
    mov_rate = float(mov_raw.info.get("sfreq") or eeg_rate)
    duration_sec = min(
        eeg.shape[1] / max(eeg_rate, 1e-6),
        ecg.shape[1] / max(ecg_rate, 1e-6),
        emg.shape[1] / max(emg_rate, 1e-6),
        mov.shape[1] / max(mov_rate, 1e-6),
    )

    eeg = eeg[:, : max(1, int(round(duration_sec * eeg_rate)))]
    ecg = ecg[:, : max(1, int(round(duration_sec * ecg_rate)))]
    emg = emg[:, : max(1, int(round(duration_sec * emg_rate)))]
    mov = mov[:, : max(1, int(round(duration_sec * mov_rate)))]

    common_len = max(1, int(round(duration_sec * eeg_rate)))
    display_names = eeg_channel_names + ["ECG", "EMG"] + [mov_raw.ch_names[index] for index in mov_idx[:3]]
    display_matrix = np.concatenate(
        [
            eeg,
            _resample_channels(ecg, common_len),
            _resample_channels(emg, common_len),
            _resample_channels(mov, common_len),
        ],
        axis=0,
    )

    subject_id, session_id, run_id = chosen_key or (None, None, None)
    return UploadBundle(
        source_name=source_name,
        sample_rate=eeg_rate,
        duration_sec=float(duration_sec),
        modality_sample_rates={
            "eeg": eeg_rate,
            "ecg": ecg_rate,
            "emg": emg_rate,
            "mov": mov_rate,
        },
        eeg=eeg.astype(np.float32),
        ecg=ecg.astype(np.float32),
        emg=emg.astype(np.float32),
        mov=mov.astype(np.float32),
        eeg_channel_names=eeg_channel_names,
        display_channel_names=display_names,
        display_matrix=display_matrix.astype(np.float32),
        primary_signal=eeg.mean(axis=0).astype(np.float32),
        subject_id=subject_id,
        session_id=session_id,
        run_id=run_id,
    )


def _load_multimodal_zip_bundle(upload, artifact: dict[str, Any] | None, metadata: dict[str, Any]) -> UploadBundle:
    raw_bytes = upload.read()
    preferred_eeg_names = list(artifact.get("eeg_channel_names", [])) if artifact else []
    meta_subject = metadata.get("subjectId") or metadata.get("patientId")
    meta_session = metadata.get("session")
    meta_run = metadata.get("run")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        with zipfile.ZipFile(Path(temp_root / "bundle.zip"), "w") as _:
            pass

        zip_path = temp_root / "bundle.zip"
        zip_path.write_bytes(raw_bytes)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(temp_root / "unzipped")

        extracted_root = temp_root / "unzipped"
        all_signal_files = [
            path
            for path in extracted_root.rglob("*")
            if path.is_file() and path.suffix.lower() in {".edf", ".bdf"}
        ]
        if not all_signal_files:
            metadata_paths = [path for path in extracted_root.rglob("*") if path.is_file()]
            return _build_metadata_bundle_from_paths(metadata_paths, metadata)

        grouped: dict[tuple[str | None, str | None, str | None], dict[str, Path]] = {}
        for path in all_signal_files:
            subject_id, session_id, run_id = _parse_identity(path.name)
            lower_name = path.name.lower()
            modality = None
            for candidate in ["eeg", "ecg", "emg", "mov"]:
                if f"_{candidate}." in lower_name or lower_name.endswith(f"{candidate}{path.suffix.lower()}"):
                    modality = candidate
                    break
            if modality is None:
                continue
            key = (subject_id, session_id, run_id)
            grouped.setdefault(key, {})[modality] = path

        chosen_key = None
        chosen_files = None
        requested_run = meta_run if str(meta_run or "").startswith("run-") else (f"run-{meta_run}" if meta_run else None)
        for key, files in grouped.items():
            if not {"eeg", "ecg", "emg", "mov"}.issubset(files):
                continue
            subject_id, session_id, run_id = key
            if meta_subject and subject_id and meta_subject != subject_id:
                continue
            if meta_session and session_id and meta_session != session_id:
                continue
            if requested_run and run_id and requested_run != run_id:
                continue
            chosen_key = key
            chosen_files = files
            break

        if chosen_files is None:
            for key, files in grouped.items():
                if {"eeg", "ecg", "emg", "mov"}.issubset(files):
                    chosen_key = key
                    chosen_files = files
                    break

        if chosen_files is None:
            metadata_paths = [path for path in extracted_root.rglob("*") if path.is_file()]
            return _build_metadata_bundle_from_paths(metadata_paths, metadata)

        try:
            eeg_raw = _load_raw_from_path(chosen_files["eeg"])
            ecg_raw = _load_raw_from_path(chosen_files["ecg"])
            emg_raw = _load_raw_from_path(chosen_files["emg"])
            mov_raw = _load_raw_from_path(chosen_files["mov"])
        except Exception:
            metadata_paths = [path for path in extracted_root.rglob("*") if path.is_file()]
            return _build_metadata_bundle_from_paths(metadata_paths, metadata)

        eeg_names = list(eeg_raw.ch_names)
        eeg_types = list(eeg_raw.get_channel_types())
        eeg_idx = _pick_indices(
            eeg_names,
            eeg_types,
            preferred_names=preferred_eeg_names,
            preferred_type="eeg",
            keywords=["bteleft", "crosstop", "bteright", "eeg"],
            count=2,
        )
        ecg = _pad_or_trim_channels(ecg_raw.get_data(), 1)
        emg = _pad_or_trim_channels(emg_raw.get_data(), 1)
        mov_idx = _pick_mov_channels_from_names(list(mov_raw.ch_names))
        mov = _pad_or_trim_channels(mov_raw.get_data(picks=mov_idx), 3)
        eeg = _pad_or_trim_channels(eeg_raw.get_data(picks=eeg_idx), 2)
        eeg_channel_names = [eeg_names[index] for index in eeg_idx[:2]]
        if len(eeg_channel_names) == 1:
            eeg_channel_names.append(f"{eeg_channel_names[0]} (dup)")

        eeg_rate = float(eeg_raw.info.get("sfreq") or DEFAULT_SAMPLE_RATE)
        ecg_rate = float(ecg_raw.info.get("sfreq") or eeg_rate)
        emg_rate = float(emg_raw.info.get("sfreq") or eeg_rate)
        mov_rate = float(mov_raw.info.get("sfreq") or eeg_rate)
        duration_sec = min(
            eeg.shape[1] / max(eeg_rate, 1e-6),
            ecg.shape[1] / max(ecg_rate, 1e-6),
            emg.shape[1] / max(emg_rate, 1e-6),
            mov.shape[1] / max(mov_rate, 1e-6),
        )

        eeg = eeg[:, : max(1, int(round(duration_sec * eeg_rate)))]
        ecg = ecg[:, : max(1, int(round(duration_sec * ecg_rate)))]
        emg = emg[:, : max(1, int(round(duration_sec * emg_rate)))]
        mov = mov[:, : max(1, int(round(duration_sec * mov_rate)))]

        common_len = max(1, int(round(duration_sec * eeg_rate)))
        display_names = eeg_channel_names + ["ECG", "EMG"] + [mov_raw.ch_names[index] for index in mov_idx[:3]]
        display_matrix = np.concatenate(
            [
                eeg,
                _resample_channels(ecg, common_len),
                _resample_channels(emg, common_len),
                _resample_channels(mov, common_len),
            ],
            axis=0,
        )

        subject_id, session_id, run_id = chosen_key or (None, None, None)
        return UploadBundle(
            source_name=getattr(upload, "name", "patient-run.zip"),
            sample_rate=eeg_rate,
            duration_sec=float(duration_sec),
            modality_sample_rates={
                "eeg": eeg_rate,
                "ecg": ecg_rate,
                "emg": emg_rate,
                "mov": mov_rate,
            },
            eeg=eeg.astype(np.float32),
            ecg=ecg.astype(np.float32),
            emg=emg.astype(np.float32),
            mov=mov.astype(np.float32),
            eeg_channel_names=eeg_channel_names,
            display_channel_names=display_names,
            display_matrix=display_matrix.astype(np.float32),
            primary_signal=eeg.mean(axis=0).astype(np.float32),
            subject_id=subject_id,
            session_id=session_id,
            run_id=run_id,
        )


class _InMemoryUpload:
    def __init__(self, name: str, payload: bytes) -> None:
        self.name = name
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


def _load_multimodal_folder_bundle(upload_files: list[Any], artifact: dict[str, Any] | None, metadata: dict[str, Any]) -> UploadBundle:
    if not upload_files:
        raise ValueError("Folder upload did not contain any signal files.")

    buffer = tempfile.SpooledTemporaryFile(max_size=128 * 1024 * 1024)
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for uploaded in upload_files:
            name = getattr(uploaded, "name", "signal.edf")
            suffix = Path(name).suffix.lower()
            if not _is_supported_upload_name(name):
                continue
            try:
                uploaded.seek(0)
            except Exception:
                pass
            archive.writestr(name, uploaded.read())

    buffer.seek(0)
    payload = buffer.read()
    if not payload:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            paths = []
            for index, uploaded in enumerate(upload_files):
                name = getattr(uploaded, "name", f"upload-{index}")
                if not _is_supported_upload_name(name):
                    continue
                try:
                    uploaded.seek(0)
                except Exception:
                    pass
                target = temp_root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(uploaded.read())
                paths.append(target)
            return _build_metadata_bundle_from_paths(paths, metadata)

    return _load_multimodal_zip_bundle(
        _InMemoryUpload("patient-folder.zip", payload),
        artifact,
        metadata,
    )


def _load_multimodal_local_folder_bundle(folder_path: str, artifact: dict[str, Any] | None, metadata: dict[str, Any]) -> UploadBundle:
    root = Path(folder_path).expanduser().resolve()
    allowed_root = PROJECT_ROOT.resolve()
    try:
        root.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError(f"Local folder must be inside {allowed_root}.") from exc

    if not root.exists() or not root.is_dir():
        raise ValueError("Local folder path does not exist or is not a directory.")

    return _load_multimodal_path_bundle(root, str(root), artifact, metadata)


def _build_upload_bundle(upload, artifact: dict[str, Any] | None, metadata: dict[str, Any]) -> UploadBundle:
    local_folder_path = metadata.get("localFolderPath") or metadata.get("folderPath")
    if local_folder_path:
        return _load_multimodal_local_folder_bundle(str(local_folder_path), artifact, metadata)
    if upload is None:
        return _build_demo_bundle()
    if isinstance(upload, (list, tuple)):
        return _load_multimodal_folder_bundle(list(upload), artifact, metadata)

    name = getattr(upload, "name", "signal-upload")
    suffix = Path(name).suffix.lower()
    if suffix == ".zip":
        return _load_multimodal_zip_bundle(upload, artifact, metadata)

    preferred_eeg_names = list(artifact.get("eeg_channel_names", [])) if artifact else []

    if _is_nifti_name(name) or suffix in {".json", ".tsv"}:
        raw_bytes = upload.read()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / name
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.write_bytes(raw_bytes)
            return _build_metadata_bundle_from_paths([temp_path], metadata)

    if suffix == ".csv":
        matrix, channel_names, sample_rate = _load_csv_matrix(upload)
        channel_types = ["misc"] * len(channel_names)
    else:
        matrix, channel_names, channel_types, sample_rate = _load_edf_like_matrix(upload)

    if matrix.ndim != 2 or matrix.shape[1] == 0:
        raise ValueError("The uploaded file did not contain usable signal samples.")

    eeg_idx = _pick_indices(
        channel_names,
        channel_types,
        preferred_names=preferred_eeg_names,
        preferred_type="eeg",
        keywords=["eeg", "fp", "f7", "f8", "t7", "t8", "c3", "c4", "pz"],
        count=2,
    )
    ecg_idx = _pick_indices(
        channel_names,
        channel_types,
        preferred_type="ecg",
        keywords=["ecg", "ekg"],
        count=1,
    )
    emg_idx = _pick_indices(
        channel_names,
        channel_types,
        preferred_type="emg",
        keywords=["emg"],
        count=1,
    )
    mov_idx = _pick_indices(
        channel_names,
        channel_types,
        preferred_type="misc",
        keywords=["acc", "gyro", "mov", "motion"],
        count=3,
    )

    eeg = _pad_or_trim_channels(matrix[eeg_idx], 2)
    ecg = _pad_or_trim_channels(matrix[ecg_idx], 1)
    emg = _pad_or_trim_channels(matrix[emg_idx], 1)
    mov = _pad_or_trim_channels(matrix[mov_idx], 3)
    eeg_channel_names = [channel_names[index] for index in eeg_idx[:2]]
    if len(eeg_channel_names) == 1:
        eeg_channel_names.append(f"{eeg_channel_names[0]} (dup)")

    display_names, display_matrix = _select_display_channels(channel_names, matrix)
    primary_signal = eeg.mean(axis=0) if eeg.size else matrix[0]
    subject_id, session_id, run_id = _parse_identity(name)

    return UploadBundle(
        source_name=name,
        sample_rate=float(sample_rate or DEFAULT_SAMPLE_RATE),
        duration_sec=float(matrix.shape[1] / max(sample_rate, 1e-6)),
        modality_sample_rates={
            "eeg": float(sample_rate or DEFAULT_SAMPLE_RATE),
            "ecg": float(sample_rate or DEFAULT_SAMPLE_RATE),
            "emg": float(sample_rate or DEFAULT_SAMPLE_RATE),
            "mov": float(sample_rate or DEFAULT_SAMPLE_RATE),
        },
        eeg=eeg.astype(np.float32),
        ecg=ecg.astype(np.float32),
        emg=emg.astype(np.float32),
        mov=mov.astype(np.float32),
        eeg_channel_names=eeg_channel_names,
        display_channel_names=display_names,
        display_matrix=display_matrix.astype(np.float32),
        primary_signal=primary_signal.astype(np.float32),
        subject_id=subject_id,
        session_id=session_id,
        run_id=run_id,
    )


def _build_demo_bundle() -> UploadBundle:
    sample_rate = DEFAULT_SAMPLE_RATE
    seconds = 60
    time = np.linspace(0.0, seconds, int(sample_rate * seconds), endpoint=False)
    eeg_left = np.sin(time * 2.1) + 0.15 * np.sin(time * 16.0)
    eeg_right = 0.8 * np.sin(time * 1.8 + 0.4) + 0.12 * np.sin(time * 14.0)
    eeg_left[18 * 256 : 21 * 256] += 1.1 * np.sin(time[: 3 * 256] * 22.0)
    eeg_right[37 * 256 : 40 * 256] += 0.8 * np.sin(time[: 3 * 256] * 18.0)
    eeg = np.stack([eeg_left, eeg_right]).astype(np.float32)
    ecg = np.sin(time * 1.2).reshape(1, -1).astype(np.float32)
    emg = (0.2 * np.sin(time * 8.0)).reshape(1, -1).astype(np.float32)
    mov = np.stack(
        [
            0.1 * np.sin(time * 0.9),
            0.08 * np.sin(time * 1.3 + 0.5),
            0.12 * np.sin(time * 0.7 + 1.0),
        ]
    ).astype(np.float32)
    display_matrix = np.concatenate([eeg, ecg, emg, mov], axis=0)
    return UploadBundle(
        source_name="demo-signal",
        sample_rate=sample_rate,
        duration_sec=seconds,
        modality_sample_rates={
            "eeg": sample_rate,
            "ecg": sample_rate,
            "emg": sample_rate,
            "mov": sample_rate,
        },
        eeg=eeg,
        ecg=ecg,
        emg=emg,
        mov=mov,
        eeg_channel_names=["BTEleft SD", "BTEright SD"],
        display_channel_names=["BTEleft SD", "BTEright SD", "ECG", "EMG", "ACC X", "ACC Y"],
        display_matrix=display_matrix[:6],
        primary_signal=eeg.mean(axis=0),
    )


def _build_metadata_demo_bundle(source_names: list[str], metadata: dict[str, Any]) -> UploadBundle:
    bundle = _build_demo_bundle()
    identity_source = " ".join(source_names)
    subject_id, session_id, run_id = _parse_identity(identity_source)
    bundle.source_name = "metadata-showcase-upload"
    bundle.subject_id = metadata.get("subjectId") or metadata.get("patientId") or subject_id
    bundle.session_id = metadata.get("session") or session_id
    requested_run = metadata.get("run") or run_id
    bundle.run_id = requested_run if not requested_run or str(requested_run).startswith("run-") else f"run-{requested_run}"
    return bundle


def _artifact_stats(artifact: dict[str, Any], modality: str) -> dict[str, np.ndarray] | None:
    stats = artifact.get("normalization_stats", {})
    value = stats.get(modality)
    if not value:
        return None
    mean = np.asarray(value["mean"], dtype=np.float32).reshape(-1, 1)
    std = np.asarray(value["std"], dtype=np.float32).reshape(-1, 1)
    return {"mean": mean, "std": std + 1e-6}


def _normalize_for_model(arr: np.ndarray, stats: dict[str, np.ndarray] | None) -> np.ndarray:
    arr = _to_float_array(arr)
    if stats is None:
        return _normalize_channelwise(arr)
    return ((arr - stats["mean"]) / stats["std"]).astype(np.float32)


def _make_window_batch(bundle: UploadBundle, artifact: dict[str, Any], start_sec: float) -> dict[str, np.ndarray]:
    window_sec = float(artifact.get("window_sec", DEFAULT_WINDOW_SEC))
    target_sr = float(artifact.get("sample_rate", DEFAULT_SAMPLE_RATE))
    target_len = max(int(round(window_sec * target_sr)), 1)
    eeg_rate = float(bundle.modality_sample_rates.get("eeg", bundle.sample_rate))
    ecg_rate = float(bundle.modality_sample_rates.get("ecg", bundle.sample_rate))
    emg_rate = float(bundle.modality_sample_rates.get("emg", bundle.sample_rate))
    mov_rate = float(bundle.modality_sample_rates.get("mov", bundle.sample_rate))

    eeg = _resample_channels(
        _extract_window(
            bundle.eeg,
            int(round(start_sec * eeg_rate)),
            max(int(round(window_sec * eeg_rate)), 1),
        ),
        target_len,
    )
    ecg = _resample_channels(
        _extract_window(
            bundle.ecg,
            int(round(start_sec * ecg_rate)),
            max(int(round(window_sec * ecg_rate)), 1),
        ),
        target_len,
    )
    emg = _resample_channels(
        _extract_window(
            bundle.emg,
            int(round(start_sec * emg_rate)),
            max(int(round(window_sec * emg_rate)), 1),
        ),
        target_len,
    )
    mov = _resample_channels(
        _extract_window(
            bundle.mov,
            int(round(start_sec * mov_rate)),
            max(int(round(window_sec * mov_rate)), 1),
        ),
        target_len,
    )

    return {
        "eeg": _normalize_for_model(eeg, _artifact_stats(artifact, "eeg")),
        "ecg": _normalize_for_model(ecg, _artifact_stats(artifact, "ecg")),
        "emg": _normalize_for_model(emg, _artifact_stats(artifact, "emg")),
        "mov": _normalize_for_model(mov, _artifact_stats(artifact, "mov")),
    }


def _torch_batch(batch_np: dict[str, np.ndarray]) -> dict[str, torch.Tensor]:
    return {
        name: torch.from_numpy(values[None, ...]).float()
        for name, values in batch_np.items()
    }


def _compute_channel_importance(model: torch.nn.Module, batch: dict[str, torch.Tensor]) -> np.ndarray:
    eeg = batch["eeg"].clone().detach().requires_grad_(True)
    forward_batch = {name: tensor.clone().detach() for name, tensor in batch.items()}
    forward_batch["eeg"] = eeg
    model.zero_grad()
    logits = model(forward_batch)
    logits[0].backward()
    grads = eeg.grad.detach().abs().mean(dim=-1).squeeze(0).cpu().numpy()
    return grads.astype(np.float32)


def _probability_from_batch(model: torch.nn.Module, batch: dict[str, torch.Tensor]) -> float:
    with torch.no_grad():
        logits = model({name: tensor.clone().detach() for name, tensor in batch.items()})
        return float(torch.sigmoid(logits)[0].item())


def _compute_modality_occlusion(model: torch.nn.Module, batch: dict[str, torch.Tensor]) -> list[dict[str, Any]]:
    base_probability = _probability_from_batch(model, batch)
    drops = []
    for modality in ["eeg", "ecg", "emg", "mov"]:
        occluded = {name: tensor.clone().detach() for name, tensor in batch.items()}
        occluded[modality] = torch.zeros_like(occluded[modality])
        occluded_probability = _probability_from_batch(model, occluded)
        drops.append(
            {
                "label": modality.upper(),
                "value": round(float(max(base_probability - occluded_probability, 0.0)), 4),
                "ablatedProbability": round(float(occluded_probability), 4),
            }
        )
    return drops


def _compute_eeg_gradcam(model: torch.nn.Module, batch: dict[str, torch.Tensor], target_len: int) -> np.ndarray:
    target_layer = getattr(getattr(model, "eeg_encoder", None), "last_conv", None)
    if target_layer is None:
        return np.zeros(target_len, dtype=np.float32)

    activations: list[torch.Tensor] = []
    gradients: list[torch.Tensor] = []

    def forward_hook(_module, _inputs, output):
        activations.append(output)

    def backward_hook(_module, _grad_input, grad_output):
        gradients.append(grad_output[0])

    forward_handle = target_layer.register_forward_hook(forward_hook)
    backward_handle = target_layer.register_full_backward_hook(backward_hook)
    try:
        forward_batch = {name: tensor.clone().detach() for name, tensor in batch.items()}
        model.zero_grad()
        logits = model(forward_batch)
        logits[0].backward()
        if not activations or not gradients:
            return np.zeros(target_len, dtype=np.float32)

        act = activations[-1].detach()
        grad = gradients[-1].detach()
        weights = grad.mean(dim=-1, keepdim=True)
        cam = torch.relu((weights * act).sum(dim=1, keepdim=True))
        cam = torch.nn.functional.interpolate(cam, size=target_len, mode="linear", align_corners=False)
        values = cam.squeeze().cpu().numpy().astype(np.float32)
        values -= float(values.min())
        scale = float(values.max())
        if scale > 1e-6:
            values /= scale
        return values
    finally:
        forward_handle.remove()
        backward_handle.remove()


def _compute_integrated_gradients_eeg(
    model: torch.nn.Module,
    batch: dict[str, torch.Tensor],
    steps: int = 24,
) -> np.ndarray:
    model.eval()
    baseline = torch.zeros_like(batch["eeg"])
    total_grads = torch.zeros_like(batch["eeg"])
    alphas = torch.linspace(0.0, 1.0, steps + 1)[1:]

    for alpha in alphas:
        interpolated = (baseline + alpha * (batch["eeg"] - baseline)).clone().detach().requires_grad_(True)
        forward_batch = {name: tensor.clone().detach() for name, tensor in batch.items()}
        forward_batch["eeg"] = interpolated
        model.zero_grad()
        logits = model(forward_batch)
        logits[0].backward()
        total_grads += interpolated.grad.detach()

    avg_grads = total_grads / max(len(alphas), 1)
    attributions = (batch["eeg"] - baseline) * avg_grads
    return attributions.detach().cpu().numpy().squeeze(0).astype(np.float32)


def _build_integrated_gradient_heatmap(
    integrated_gradients: np.ndarray,
    channel_names: list[str],
    sample_rate: float,
    start_sec: float,
    max_points: int = 140,
) -> list[dict[str, Any]]:
    if integrated_gradients.size == 0:
        return []
    values = np.abs(np.asarray(integrated_gradients, dtype=np.float32))
    scale = float(values.max())
    if scale > 1e-6:
        values = values / scale

    stride = max(1, int(np.ceil(values.shape[1] / max_points)))
    rows: list[dict[str, Any]] = []
    for channel_index in range(values.shape[0]):
        channel_name = channel_names[channel_index] if channel_index < len(channel_names) else f"EEG {channel_index + 1}"
        for start in range(0, values.shape[1], stride):
            chunk = values[channel_index, start : start + stride]
            rows.append(
                {
                    "channel": channel_name,
                    "t": round(float(start_sec + start / max(sample_rate, 1e-6)), 2),
                    "v": round(float(chunk.mean()), 4),
                }
            )
    return rows


def _important_segment_from_cam(cam: np.ndarray, start_sec: float, window_sec: float, sample_rate: float) -> dict[str, float] | None:
    if cam.size == 0 or not np.isfinite(cam).any():
        return None
    segment_len = max(1, int(round(min(2.0, window_sec) * sample_rate)))
    if cam.size <= segment_len:
        local_start = 0
    else:
        kernel = np.ones(segment_len, dtype=np.float32) / segment_len
        smoothed = np.convolve(cam.astype(np.float32), kernel, mode="valid")
        local_start = int(np.argmax(smoothed))
    local_end = min(local_start + segment_len, cam.size)
    return {
        "start": round(float(start_sec + local_start / max(sample_rate, 1e-6)), 2),
        "end": round(float(start_sec + local_end / max(sample_rate, 1e-6)), 2),
    }


def _build_gradcam_points(cam: np.ndarray, start_sec: float, sample_rate: float, max_points: int = 180) -> list[dict[str, float]]:
    if cam.size == 0:
        return []
    stride = max(1, int(np.ceil(cam.size / max_points)))
    points = []
    for start in range(0, cam.size, stride):
        chunk = cam[start : start + stride]
        points.append(
            {
                "t": round(float(start_sec + start / max(sample_rate, 1e-6)), 2),
                "v": round(float(chunk.mean()), 4),
            }
        )
    return points


def _run_torch_model(bundle: UploadBundle, loaded: LoadedAxis7Model) -> dict[str, Any]:
    artifact = loaded.artifact
    model = loaded.model
    window_sec = float(artifact.get("window_sec", DEFAULT_WINDOW_SEC))
    step_sec = float(artifact.get("step_sec", window_sec / 2.0))
    window_len = max(int(round(window_sec * bundle.sample_rate)), 1)
    step_len = max(int(round(step_sec * bundle.sample_rate)), 1)
    starts = _window_starts(bundle.primary_signal.size, window_len, step_len)
    max_windows = int(artifact.get("max_web_windows", 48))
    if len(starts) > max_windows:
        starts = [starts[index] for index in np.linspace(0, len(starts) - 1, max_windows, dtype=int)]

    scores = []
    top_score = -1.0
    top_batch: dict[str, torch.Tensor] | None = None
    top_attention: np.ndarray | None = None
    top_midpoint = 0.0
    top_start_sec = 0.0

    for start in starts:
        start_sec = start / max(bundle.sample_rate, 1e-6)
        batch_np = _make_window_batch(bundle, artifact, start_sec)
        batch = _torch_batch(batch_np)

        attention = None
        with torch.no_grad():
            if hasattr(model, "attention"):
                outputs = model(batch, return_attention=True)
                logits, attention = outputs[0], outputs[1]
                attention = attention.squeeze(0).cpu().numpy()
            else:
                logits = model(batch)
            probability = float(torch.sigmoid(logits)[0].item())

        midpoint = (start + window_len / 2) / max(bundle.sample_rate, 1e-6)
        scores.append({"start": start_sec, "t": midpoint, "prob": probability})
        if probability > top_score:
            top_score = probability
            top_batch = batch
            top_attention = attention
            top_midpoint = midpoint
            top_start_sec = start_sec

    if top_batch is None:
        raise ValueError("No windows were generated for Axis 7 inference.")

    channel_importance = _compute_channel_importance(model, top_batch)
    target_sr = float(artifact.get("sample_rate", DEFAULT_SAMPLE_RATE))
    target_len = max(int(round(window_sec * target_sr)), 1)
    gradcam = _compute_eeg_gradcam(model, top_batch, target_len)
    integrated_gradients = _compute_integrated_gradients_eeg(model, top_batch)
    ig_channel_importance = np.abs(integrated_gradients).mean(axis=1).astype(np.float32)
    return {
        "window_scores": scores,
        "top_probability": float(top_score),
        "top_midpoint": float(top_midpoint),
        "top_start_sec": float(top_start_sec),
        "channel_importance": channel_importance,
        "ig_channel_importance": ig_channel_importance,
        "integrated_gradients": integrated_gradients,
        "attention_weights": top_attention,
        "modality_occlusion": _compute_modality_occlusion(model, top_batch),
        "gradcam_points": _build_gradcam_points(gradcam, top_start_sec, target_sr),
        "important_segment": _important_segment_from_cam(gradcam, top_start_sec, window_sec, target_sr),
        "source_label": loaded.label,
    }


def _heuristic_window_scores(bundle: UploadBundle) -> dict[str, Any]:
    sample_rate = max(bundle.sample_rate, 1e-6)
    window_sec = DEFAULT_WINDOW_SEC
    step_sec = window_sec / 2.0
    window_len = max(int(round(window_sec * sample_rate)), 1)
    step_len = max(int(round(step_sec * sample_rate)), 1)
    starts = _window_starts(bundle.primary_signal.size, window_len, step_len)

    features = []
    channel_matrix = bundle.display_matrix if bundle.display_matrix.size else bundle.eeg
    channel_line_length = np.abs(np.diff(channel_matrix, axis=1)).mean(axis=1) if channel_matrix.shape[1] > 1 else np.ones(channel_matrix.shape[0])

    for start in starts:
        window = _extract_window(bundle.eeg, start, window_len)
        line_length = float(np.abs(np.diff(window, axis=1)).mean())
        variance = float(window.std())
        peak = float(np.percentile(np.abs(window), 97))
        features.append((start, line_length, variance, peak))

    values = np.asarray([[item[1], item[2], item[3]] for item in features], dtype=np.float32)
    means = values.mean(axis=0, keepdims=True)
    stds = values.std(axis=0, keepdims=True) + 1e-6
    normalized = (values - means) / stds
    raw_scores = 0.5 * normalized[:, 0] + 0.3 * normalized[:, 1] + 0.2 * normalized[:, 2]
    probabilities = 1.0 / (1.0 + np.exp(-raw_scores))

    scores = []
    for (start, _, _, _), probability in zip(features, probabilities):
        midpoint = (start + window_len / 2) / sample_rate
        scores.append({"start": start / sample_rate, "t": midpoint, "prob": float(probability)})

    best_index = int(np.argmax(probabilities))
    return {
        "window_scores": scores,
        "top_probability": float(probabilities[best_index]),
        "top_midpoint": float(scores[best_index]["t"]),
        "top_start_sec": float(scores[best_index]["start"]),
        "channel_importance": channel_line_length.astype(np.float32),
        "ig_channel_importance": channel_line_length.astype(np.float32),
        "integrated_gradients": np.empty((0, 0), dtype=np.float32),
        "attention_weights": None,
        "modality_occlusion": [],
        "gradcam_points": [],
        "important_segment": None,
        "source_label": "Signal heuristic",
    }


def _metadata_window_scores(bundle: UploadBundle) -> dict[str, Any]:
    summary = bundle.metadata_summary or {}
    seizure_events = list(summary.get("seizure_events") or [])
    excluded_events = list(summary.get("excluded_events") or [])
    event_count = len(summary.get("events") or [])
    window_scores = []
    sample_rate = max(bundle.sample_rate, 1e-6)
    window_sec = DEFAULT_WINDOW_SEC
    window_len = max(int(round(window_sec * sample_rate)), 1)
    step_len = max(int(round(window_sec * sample_rate)), 1)
    starts = _window_starts(bundle.primary_signal.size, window_len, step_len)
    starts = [starts[index] for index in np.linspace(0, len(starts) - 1, min(len(starts), 24), dtype=int)]

    if seizure_events:
        base_probability = 0.78
    elif excluded_events:
        base_probability = 0.32
    elif event_count:
        base_probability = 0.24
    else:
        base_probability = 0.18

    original_duration = float(summary.get("recording_duration") or bundle.duration_sec)
    scale = bundle.duration_sec / max(original_duration, bundle.duration_sec, 1.0)
    seizure_times = [float(event["onset"]) * scale for event in seizure_events]
    for start in starts:
        midpoint = (start + window_len / 2) / sample_rate
        probability = base_probability
        if seizure_times:
            distance = min(abs(midpoint - event_time) for event_time in seizure_times)
            probability = max(probability, 0.85 * float(np.exp(-(distance**2) / (2 * 12.0**2))))
        window_scores.append({"start": start / sample_rate, "t": midpoint, "prob": float(np.clip(probability, 0.02, 0.95))})

    best_index = int(np.argmax([item["prob"] for item in window_scores])) if window_scores else 0
    channel_importance = np.asarray([0.58, 0.42], dtype=np.float32)
    return {
        "window_scores": window_scores,
        "top_probability": float(window_scores[best_index]["prob"] if window_scores else base_probability),
        "top_midpoint": float(window_scores[best_index]["t"] if window_scores else bundle.duration_sec / 2),
        "top_start_sec": float(window_scores[best_index]["start"] if window_scores else 0.0),
        "channel_importance": channel_importance,
        "ig_channel_importance": channel_importance,
        "integrated_gradients": np.empty((0, 0), dtype=np.float32),
        "attention_weights": None,
        "modality_occlusion": [
            {"label": "EEG", "value": round(float(base_probability * 0.45), 4), "ablatedProbability": round(float(base_probability * 0.55), 4)},
            {"label": "ECG", "value": round(float(base_probability * 0.08), 4), "ablatedProbability": round(float(base_probability * 0.92), 4)},
            {"label": "EMG", "value": round(float(base_probability * 0.12), 4), "ablatedProbability": round(float(base_probability * 0.88), 4)},
            {"label": "MOV", "value": round(float(base_probability * 0.10), 4), "ablatedProbability": round(float(base_probability * 0.90), 4)},
        ],
        "gradcam_points": build_signal(np.abs(bundle.primary_signal), bundle.sample_rate),
        "important_segment": {"start": 0.0, "end": 2.0},
        "source_label": "BIDS metadata showcase",
    }


def _legacy_predict(bundle: UploadBundle, loaded: LoadedAxis7Model) -> dict[str, Any]:
    signal = _normalize_channelwise(bundle.eeg)
    features = np.asarray(
        [
            signal.mean(axis=1),
            signal.std(axis=1),
            np.abs(np.diff(signal, axis=1)).mean(axis=1),
        ],
        dtype=np.float32,
    ).reshape(1, -1)
    model = loaded.model
    if hasattr(model, "predict_proba"):
        probability = float(model.predict_proba(features)[0][-1])
    else:
        probability = float(np.clip(model.predict(features)[0], 0.0, 1.0))
    importance = np.abs(signal).mean(axis=1)
    return {
        "window_scores": [{"start": 0.0, "t": bundle.duration_sec / 2.0, "prob": probability}],
        "top_probability": probability,
        "top_midpoint": bundle.duration_sec / 2.0,
        "top_start_sec": 0.0,
        "channel_importance": importance.astype(np.float32),
        "ig_channel_importance": importance.astype(np.float32),
        "integrated_gradients": np.empty((0, 0), dtype=np.float32),
        "attention_weights": None,
        "modality_occlusion": [],
        "gradcam_points": [],
        "important_segment": None,
        "source_label": loaded.label,
    }


def _build_timeline_events(window_scores: list[dict[str, Any]], dominant_channel: str) -> list[dict[str, Any]]:
    events = []
    for window in sorted(window_scores, key=lambda item: item["prob"], reverse=True):
        probability = float(window["prob"])
        if probability < 0.42 and events:
            continue
        if probability >= 0.75:
            severity = "high"
            label = f"{dominant_channel} high-instability window"
        elif probability >= 0.55:
            severity = "moderate"
            label = f"{dominant_channel} elevated activity"
        else:
            severity = "low"
            label = f"{dominant_channel} mild fluctuation"
        events.append({"t": window["t"], "severity": severity, "label": label})
        if len(events) >= 5:
            break

    if not events and window_scores:
        peak = max(window_scores, key=lambda item: item["prob"])
        events.append({"t": peak["t"], "severity": "low", "label": f"{dominant_channel} review window"})
    return events


def _build_summary(probability: float, dominant_channel: str, event_count: int, peak_time: float, source_label: str) -> str:
    if probability >= 0.7:
        return (
            f"Repeated seizure-like instability is concentrated around {dominant_channel}, with the peak window near "
            f"{peak_time:.1f}s. {event_count} elevated window(s) were flagged in this recording."
        )
    if probability >= 0.45:
        return (
            f"Intermittent instability is present, strongest around {dominant_channel} near {peak_time:.1f}s. "
            f"This supports moderate epilepsy vulnerability and should be reviewed with the raw trace."
        )
    return (
        f"The analyzed recording is relatively stable overall, with only limited fluctuations around {dominant_channel}. "
        f"The current estimate came from the {source_label.lower()} pipeline."
    )


_FMRI_XAI_CACHE: dict[str, Any] | None = None


def _format_coord_mm(coord: np.ndarray) -> tuple[float, float, float]:
    return tuple(round(float(value), 2) for value in coord[:3])


def _infer_hemisphere(x_coord: float) -> str:
    if x_coord < -5:
        return "left"
    if x_coord > 5:
        return "right"
    return "midline"


def _top_voxel_rows(data: np.ndarray, affine: np.ndarray, metric_name: str, top_k: int = 5) -> list[dict[str, Any]]:
    flat = data.reshape(-1)
    top_k = min(top_k, flat.size)
    top_indices = np.argpartition(flat, -top_k)[-top_k:]
    top_indices = top_indices[np.argsort(flat[top_indices])[::-1]]
    rows = []
    for rank, flat_index in enumerate(top_indices, start=1):
        voxel_index = tuple(int(i) for i in np.unravel_index(int(flat_index), data.shape))
        coord_mm = _format_coord_mm(affine @ np.asarray([*voxel_index, 1.0]))
        rows.append(
            {
                "rank": rank,
                "metric": metric_name,
                "value": round(float(flat[int(flat_index)]), 6),
                "voxel_index": str(voxel_index),
                "coord_mm": str(coord_mm),
                "hemisphere": _infer_hemisphere(coord_mm[0]),
            }
        )
    return rows


def _slice_to_data_url(
    base_data: np.ndarray,
    title: str,
    *,
    overlay: np.ndarray | None = None,
    voxel: tuple[int, int, int] | None = None,
) -> str:
    plt = _import_matplotlib_pyplot()
    z_index = voxel[2] if voxel else base_data.shape[2] // 2
    z_index = int(np.clip(z_index, 0, base_data.shape[2] - 1))

    fig, ax = plt.subplots(figsize=(4, 4), dpi=120)
    ax.imshow(np.rot90(base_data[:, :, z_index]), cmap="gray")
    if overlay is not None:
        overlay_slice = np.rot90(overlay[:, :, z_index])
        masked = np.ma.masked_where(overlay_slice <= 0, overlay_slice)
        ax.imshow(masked, cmap="hot", alpha=0.65)
    ax.set_title(title, fontsize=9)
    ax.axis("off")
    fig.tight_layout(pad=0.1)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _extract_fmri_xai() -> dict[str, Any] | None:
    global _FMRI_XAI_CACHE
    if _FMRI_XAI_CACHE is not None:
        return _FMRI_XAI_CACHE

    try:
        if FMRI_PATH.exists():
            import nibabel as nib

            img = nib.load(str(FMRI_PATH))
            data = img.get_fdata(dtype=np.float32)
            affine = img.affine
            shape_value = tuple(int(v) for v in img.shape)
            source_note = "Post-hoc fMRI summary from ds007313 is illustrative and not subject-matched to the wearable seizure recording."
        else:
            grid = np.linspace(-1.0, 1.0, 48, dtype=np.float32)
            x, y, z = np.meshgrid(grid, grid, grid, indexing="ij")
            mean_blob = np.exp(-((x + 0.35) ** 2 + (y - 0.1) ** 2 + (z + 0.05) ** 2) / 0.08)
            std_blob = np.exp(-((x - 0.25) ** 2 + (y + 0.15) ** 2 + (z - 0.2) ** 2) / 0.05)
            time = np.linspace(0, 2 * np.pi, 24, dtype=np.float32)
            data = np.stack([mean_blob + 0.18 * np.sin(t) * std_blob for t in time], axis=-1).astype(np.float32)
            affine = np.eye(4, dtype=np.float32)
            shape_value = data.shape
            source_note = "Synthetic fMRI-style XAI image generated because the notebook ds007313 NIfTI file was not found on this computer."

        if data.ndim == 4:
            mean_data = np.nanmean(data, axis=-1).astype(np.float32)
            std_data = np.nanstd(data, axis=-1).astype(np.float32)
            temporal_profile = np.nanmean(data, axis=(0, 1, 2)).astype(np.float32)
            n_timepoints = int(data.shape[-1])
        else:
            mean_data = data.astype(np.float32)
            std_data = np.zeros_like(mean_data, dtype=np.float32)
            temporal_profile = np.array([float(np.nanmean(data))], dtype=np.float32)
            n_timepoints = 1

        peak_mean_voxel = tuple(int(i) for i in np.unravel_index(int(np.nanargmax(mean_data)), mean_data.shape))
        peak_std_voxel = tuple(int(i) for i in np.unravel_index(int(np.nanargmax(std_data)), std_data.shape))
        peak_mean_coord = _format_coord_mm(affine @ np.asarray([*peak_mean_voxel, 1.0]))
        peak_std_coord = _format_coord_mm(affine @ np.asarray([*peak_std_voxel, 1.0]))
        mean_hotspot_threshold = float(np.nanpercentile(mean_data, 99.5))
        std_hotspot_threshold = float(np.nanpercentile(std_data, 99.5))
        mean_hotspot = np.where(mean_data >= mean_hotspot_threshold, mean_data, 0.0).astype(np.float32)
        std_hotspot = np.where(std_data >= std_hotspot_threshold, std_data, 0.0).astype(np.float32)

        temporal_stride = max(1, int(np.ceil(temporal_profile.size / 160)))
        temporal_points = [
            {"t": int(index), "v": round(float(temporal_profile[index : index + temporal_stride].mean()), 6)}
            for index in range(0, temporal_profile.size, temporal_stride)
        ]

        table = [
            {"feature": "shape", "value": str(shape_value)},
            {"feature": "timepoints", "value": n_timepoints},
            {"feature": "mean_activation", "value": round(float(np.nanmean(data)), 6)},
            {"feature": "variance", "value": round(float(np.nanvar(data)), 6)},
            {"feature": "min", "value": round(float(np.nanmin(data)), 6)},
            {"feature": "max", "value": round(float(np.nanmax(data)), 6)},
            {"feature": "peak_mean_coord_mm", "value": str(peak_mean_coord)},
            {"feature": "peak_mean_hemisphere", "value": _infer_hemisphere(peak_mean_coord[0])},
            {"feature": "peak_std_coord_mm", "value": str(peak_std_coord)},
            {"feature": "peak_std_hemisphere", "value": _infer_hemisphere(peak_std_coord[0])},
            {"feature": "mean_hotspot_threshold", "value": round(mean_hotspot_threshold, 6)},
            {"feature": "mean_hotspot_fraction", "value": round(float(np.mean(mean_data >= mean_hotspot_threshold)), 6)},
            {"feature": "std_hotspot_threshold", "value": round(std_hotspot_threshold, 6)},
            {"feature": "std_hotspot_fraction", "value": round(float(np.mean(std_data >= std_hotspot_threshold)), 6)},
            {
                "feature": "temporal_profile_range",
                "value": f"{float(np.min(temporal_profile)):.4f} to {float(np.max(temporal_profile)):.4f}",
            },
        ]

        _FMRI_XAI_CACHE = {
            "table": table,
            "meanTopVoxels": _top_voxel_rows(mean_data, affine, "mean_activation"),
            "stdTopVoxels": _top_voxel_rows(std_data, affine, "temporal_std"),
            "temporalProfile": temporal_points,
            "images": [
                {"title": "Mean denoised fMRI activation", "dataUrl": _slice_to_data_url(mean_data, "Mean fMRI", voxel=peak_mean_voxel)},
                {
                    "title": "Mean-activation hotspot",
                    "dataUrl": _slice_to_data_url(mean_data, "Mean hotspot", overlay=mean_hotspot, voxel=peak_mean_voxel),
                },
                {
                    "title": "Temporal-variability hotspot",
                    "dataUrl": _slice_to_data_url(mean_data, "Temporal std hotspot", overlay=std_hotspot, voxel=peak_std_voxel),
                },
            ],
            "interpretation": (
                f"{source_note} The strongest mean-activation hotspot is near {peak_mean_coord} mm in the "
                f"{_infer_hemisphere(peak_mean_coord[0])} hemisphere."
            ),
        }
        return _FMRI_XAI_CACHE
    except Exception as exc:
        return {"error": f"fMRI XAI unavailable: {exc}"}


def predict(upload, model: Optional[LoadedAxis7Model], metadata: dict) -> dict:
    try:
        bundle = _build_upload_bundle(upload, model.artifact if model else {}, metadata)
    except Exception:
        if upload is None:
            bundle = _build_demo_bundle()
        else:
            raise

    inference_error = None
    analysis: dict[str, Any]

    if bundle.metadata_summary:
        analysis = _metadata_window_scores(bundle)
    elif model is not None:
        try:
            if model.kind == "torch":
                analysis = _run_torch_model(bundle, model)
            elif model.kind == "joblib":
                analysis = _legacy_predict(bundle, model)
            else:
                analysis = _heuristic_window_scores(bundle)
        except Exception as exc:
            inference_error = str(exc)
            analysis = _heuristic_window_scores(bundle)
    else:
        analysis = _heuristic_window_scores(bundle)

    top_probability = float(analysis["top_probability"])
    confidence = _score_to_confidence(top_probability)
    predicted_class = _predicted_class(top_probability)

    channel_importance = np.asarray(analysis["channel_importance"], dtype=np.float32)
    if channel_importance.size == 0:
        channel_importance = np.ones(len(bundle.eeg_channel_names), dtype=np.float32)

    region_channel_names = bundle.eeg_channel_names
    if channel_importance.size > len(region_channel_names):
        region_channel_names = bundle.display_channel_names[: channel_importance.size]

    dominant_index = int(np.argmax(channel_importance))
    dominant_channel = (
        region_channel_names[dominant_index]
        if dominant_index < len(region_channel_names)
        else f"Channel {dominant_index + 1}"
    )

    timeline_events = _build_timeline_events(analysis["window_scores"], dominant_channel)
    signal_points = build_signal(_normalize_channelwise(bundle.primary_signal.reshape(1, -1))[0], bundle.sample_rate)
    regions = build_regions(region_channel_names, channel_importance)
    network = build_network(bundle.display_channel_names, _normalize_channelwise(bundle.display_matrix))
    windows_flagged = sum(float(item["prob"]) >= 0.55 for item in analysis["window_scores"])

    metrics = [
        {"label": "Vulnerability index", "value": f"{top_probability * 100:.0f}%"},
        {"label": "Peak window", "value": f"{analysis['top_midpoint']:.1f}s"},
        {"label": "Windows flagged", "value": f"{windows_flagged} / {len(analysis['window_scores'])}"},
        {"label": "Dominant channel", "value": dominant_channel},
        {"label": "Signal duration", "value": f"{bundle.duration_sec:.1f} s"},
        {"label": "Inference source", "value": analysis["source_label"]},
    ]

    attention_weights = analysis.get("attention_weights")
    xai_attention = []
    if attention_weights is not None:
        modalities = ["EEG", "ECG", "EMG", "MOV"]
        dominant_modality = modalities[int(np.argmax(attention_weights))]
        metrics.append({"label": "Dominant modality", "value": dominant_modality})
        xai_attention = [
            {"label": modalities[index], "value": round(float(value), 4)}
            for index, value in enumerate(np.asarray(attention_weights, dtype=np.float32))
        ]

    modality_occlusion = list(analysis.get("modality_occlusion") or [])
    if modality_occlusion:
        occlusion_driver = max(modality_occlusion, key=lambda item: float(item.get("value", 0.0)))
        metrics.append({"label": "Occlusion driver", "value": str(occlusion_driver["label"])})

    ig_channel_importance = np.asarray(analysis.get("ig_channel_importance", []), dtype=np.float32)
    if ig_channel_importance.size:
        ig_dominant_index = int(np.argmax(ig_channel_importance))
        ig_dominant_channel = (
            region_channel_names[ig_dominant_index]
            if ig_dominant_index < len(region_channel_names)
            else f"Channel {ig_dominant_index + 1}"
        )
        metrics.append({"label": "IG dominant channel", "value": ig_dominant_channel})
    else:
        ig_dominant_channel = dominant_channel

    important_segment = analysis.get("important_segment")
    if important_segment:
        metrics.append(
            {
                "label": "XAI time focus",
                "value": f"{important_segment['start']:.2f}-{important_segment['end']:.2f}s",
            }
        )

    if bundle.subject_id:
        metrics.append({"label": "Subject", "value": bundle.subject_id})
    if bundle.session_id:
        metrics.append({"label": "Session", "value": bundle.session_id})
    if bundle.run_id:
        metrics.append({"label": "Run", "value": bundle.run_id})

    if bundle.metadata_summary:
        summary_meta = bundle.metadata_summary
        if summary_meta.get("recording_duration"):
            metrics.append({"label": "BIDS recording duration", "value": f"{float(summary_meta['recording_duration']):.1f} s"})
        metrics.append({"label": "BIDS events read", "value": str(len(summary_meta.get("events") or []))})
        metrics.append({"label": "Seizure events", "value": str(len(summary_meta.get("seizure_events") or []))})
        if summary_meta.get("excluded_events"):
            metrics.append({"label": "Excluded IMPD events", "value": str(len(summary_meta.get("excluded_events") or []))})

    if inference_error:
        metrics.append({"label": "Fallback", "value": "Notebook model unavailable for this upload"})

    summary = _build_summary(
        probability=top_probability,
        dominant_channel=dominant_channel,
        event_count=windows_flagged,
        peak_time=float(analysis["top_midpoint"]),
        source_label=str(analysis["source_label"]),
    )

    disclaimer = (
        "Axis 7 is a decision-support estimate. Interpret together with the raw EEG/signal review and clinical context; "
        "it is not a standalone seizure diagnosis or prediction."
    )

    return {
        "predictedClass": predicted_class,
        "topConfidence": max(item["value"] for item in confidence),
        "confidence": confidence,
        "summary": summary,
        "disclaimer": disclaimer,
        "regions": regions,
        "signal": signal_points,
        "timeline": build_timeline(timeline_events, dominant_channel),
        "network": network,
        "metrics": metrics,
        "xai": {
            "dominantEegChannel": dominant_channel,
            "igDominantEegChannel": ig_dominant_channel,
            "importantTimeSegment": important_segment,
            "attentionWeights": xai_attention,
            "modalityOcclusion": modality_occlusion,
            "gradcam": analysis.get("gradcam_points") or [],
            "integratedGradients": {
                "channelImportance": [
                    {
                        "label": region_channel_names[index] if index < len(region_channel_names) else f"Channel {index + 1}",
                        "value": round(float(value), 4),
                    }
                    for index, value in enumerate(ig_channel_importance)
                ],
                "heatmap": _build_integrated_gradient_heatmap(
                    np.asarray(analysis.get("integrated_gradients", np.empty((0, 0))), dtype=np.float32),
                    region_channel_names,
                    float((model.artifact if model else {}).get("sample_rate", DEFAULT_SAMPLE_RATE)),
                    float(analysis.get("top_start_sec", 0.0)),
                ),
            },
            "fmri": _extract_fmri_xai(),
            "peakWindow": {
                "start": round(float(analysis.get("top_start_sec", 0.0)), 2),
                "midpoint": round(float(analysis["top_midpoint"]), 2),
                "probability": round(top_probability, 4),
            },
        },
    }
