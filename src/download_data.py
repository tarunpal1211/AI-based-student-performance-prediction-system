"""
src/download_data.py
--------------------
Helper script to download the UCI Student Performance dataset.

Usage
-----
    python src/download_data.py

Downloads student-mat.csv and student-por.csv to data/raw/.
"""

import os
import urllib.request
import zipfile
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")
ZIP_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00320/student.zip"
ZIP_PATH = os.path.join(RAW_DIR, "student.zip")


def download():
    os.makedirs(RAW_DIR, exist_ok=True)

    print(f"Downloading UCI Student Performance dataset...")
    print(f"URL: {ZIP_URL}")

    try:
        urllib.request.urlretrieve(ZIP_URL, ZIP_PATH)
        print(f"Downloaded to {ZIP_PATH}")
    except Exception as e:
        print(f"Error downloading: {e}")
        print("\nAlternative: Download manually from:")
        print("  https://archive.ics.uci.edu/dataset/320/student+performance")
        print(f"Extract student-mat.csv and student-por.csv to: {RAW_DIR}")
        sys.exit(1)

    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        members = zf.namelist()
        print(f"Archive contains: {members}")
        for member in members:
            basename = os.path.basename(member)
            if basename in ("student-mat.csv", "student-por.csv"):
                with zf.open(member) as source:
                    dest = os.path.join(RAW_DIR, basename)
                    with open(dest, "wb") as f:
                        f.write(source.read())
                print(f"Extracted: {dest}")

    # ZipFile is closed now — safe to remove on Windows
    try:
        os.remove(ZIP_PATH)
    except PermissionError:
        print(f"Note: Could not delete {ZIP_PATH} (still locked). You can delete it manually.")
    print("\n[OK] Data ready in data/raw/")


if __name__ == "__main__":
    download()
