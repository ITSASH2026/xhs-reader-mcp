"""Remove temporary content while leaving open runtime databases intact."""
from pathlib import Path

DOWNLOAD=Path('/app/Volume/Download')
DATABASE_SUFFIXES={'.db','.sqlite','.sqlite3','.db-wal','.db-shm'}


def clean_media(root=DOWNLOAD):
    root=Path(root)
    if not root.exists():
        return
    if root.is_symlink() or root.resolve()!=root.absolute():
        raise RuntimeError('Temporary media root is not a direct directory.')
    for path in root.rglob('*'):
        if path.is_file() and path.suffix.lower() not in DATABASE_SUFFIXES:
            path.unlink()
