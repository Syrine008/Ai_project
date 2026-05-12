"""Training-aligned constants for OASIS brain-age EfficientNet-B0 (notebook 2, refinement B)."""

# Axial slice index used when extracting a single slice from a 3D volume (training used 60–139).
SLICE_INDEX_DEFAULT = 99

# Validation subject MAE (years) — README / Brief_Report figure for UI disclosure.
TYPICAL_MAE_YEARS = 4.34

# Input tensor size for EfficientNet-B0.
INPUT_SIZE = 224
