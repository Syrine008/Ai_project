"""Install a notebook export: python -m axis3_cerebellar_dysfunction.install_bundle bundle.zip"""
import argparse
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import zipfile
from .ml.inference import CerebellumLoader

NAMES = {"stage1.pth", "stage2.pth", "mni_template.nii.gz", "manifest.json", "parity.json"}


def install(archive, destination=None):
    target = Path(destination) if destination else Path(__file__).parent / "ml/artifacts"
    with TemporaryDirectory(prefix="cerebellum_install_") as directory:
        staged = Path(directory)
        with zipfile.ZipFile(archive) as bundle:
            if len(bundle.infolist()) != len(NAMES) or set(bundle.namelist()) != NAMES:
                raise ValueError("Expected exactly the five files produced by export_cerebellum.py.")
            if sum(entry.file_size for entry in bundle.infolist()) > 128 * 1024 * 1024:
                raise ValueError("Model bundle exceeds 128 MB.")
            for name in NAMES:
                with bundle.open(name) as source, (staged / name).open("wb") as output:
                    shutil.copyfileobj(source, output)
        CerebellumLoader(staged).get()  # Validate labels, weights, and notebook prediction parity before installation.
        target.mkdir(parents=True, exist_ok=True)
        for name in NAMES:
            shutil.copyfile(staged / name, target / name)
    print(f"Validated and installed cerebellum bundle in {target}. Restart the backend.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    install(args.archive, args.destination)
