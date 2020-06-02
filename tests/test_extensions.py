import pytest
from flask_googlestorage.extensions import (
    TEXT,
    DOCUMENTS,
    IMAGES,
    AUDIO,
    DATA,
    SCRIPTS,
    ARCHIVES,
    SOURCE,
    EXECUTABLES,
    ALL,
    AllExcept,
)


@pytest.mark.parametrize(
    "ext", TEXT + DOCUMENTS + IMAGES + AUDIO + DATA + SCRIPTS + ARCHIVES + SOURCE + EXECUTABLES
)
def test_all(ext):
    assert ext in ALL


@pytest.mark.parametrize(
    "exts, allowed",
    [
        (TEXT + DOCUMENTS + IMAGES + AUDIO + DATA + SCRIPTS + ARCHIVES + SOURCE, True),
        (EXECUTABLES, False),
    ],
)
def test_all_except(exts, allowed):
    ax = AllExcept(EXECUTABLES)
    if allowed:
        assert all(e in ax for e in exts)
    else:
        assert not any(e in ax for e in exts)
