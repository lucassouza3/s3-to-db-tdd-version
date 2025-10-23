import sys
from pathlib import Path


def pytest_sessionstart(session):
    # Garante que o pacote em ./project seja importável como raiz
    repo_root = Path(__file__).resolve().parents[1]
    project_dir = repo_root / "project"
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))

