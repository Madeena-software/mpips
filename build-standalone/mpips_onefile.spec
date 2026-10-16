# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import os
from pathlib import Path
block_cipher = None
REPO_ROOT = Path(SPECPATH).resolve().parent

# Collect submodules and data files
hiddenimports = [
    'mpips',
    'mpips.conversion',
    'mpips.conversion.service',
    'mpips.conversion.worker',
    'mpips.conversion.tiff_json_to_dcm',
    'mpips.conversion.validation',
    'mpips.conversion.dicom_enrichment',
    'mpips.conversion.metadata',
    'mpips.workflows.imager_pipeline',
    'mpips.workflows.imager_pipeline.npz_io',
    'mpips.workflows.imager_pipeline.pipeline',
    'mpips.processing.radiography',
    'mpips.processing.geometry',
    'mpips.processing.filtering',
    'mpips.processing.correction',
    'mpips.processing.intensity',
    'mpips.processing.thresholding',
    'mpips.processing.bit_depth',
    'mpips.pipelines.config',
    'mpips.pipelines.radiography',
    'mpips.api.schemas.dicom',
    'pydicom.encoders.native',
    'pydicom.encoders.gdcm',
    'pydicom.encoders.pylibjpeg',
    'scipy.ndimage',
    'scipy.spatial',
    'skimage',
    'cv2',
    'numpy',
]
hiddenimports += collect_submodules('mpips')
hiddenimports += collect_submodules('pydicom')

# Embed synthetic calibration assets
datas = [
    (str(REPO_ROOT / 'mpips' / 'resources' / 'calibration'), 'mpips/resources/calibration'),
]

a = Analysis(
    [str(REPO_ROOT / 'mpips' / 'standalone_runtime.py')],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'torch', 'triton', 'nvidia'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Stage B: One-file executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='mpips-runtime.bin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
