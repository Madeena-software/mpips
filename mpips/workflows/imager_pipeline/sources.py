"""Resolve Colab inputs from public Drive links or mounted filesystem paths."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Callable


class SourceResolutionError(ValueError):
    pass


def _normalize_specs(specs: str | Path | Sequence[str | Path]) -> list[str]:
    if isinstance(specs, (str, Path)):
        text = str(specs).strip()
        if "\n" in text:
            return [line.strip() for line in text.splitlines() if line.strip()]
        return [text] if text else []
    return [str(item).strip() for item in specs if str(item).strip()]


def _is_url(value: str) -> bool:
    return value.startswith("https://") or value.startswith("http://")


def resolve_npz_sources(
    specs: str | Path | Sequence[str | Path],
    destination: str | Path,
    *,
    downloader: Callable[[str, Path, bool], object] | None = None,
) -> list[Path]:
    """Resolve file/list/folder specifications to a stable sorted NPZ list."""
    destination_path = Path(destination)
    destination_path.mkdir(parents=True, exist_ok=True)

    resolved: list[Path] = []
    for index, spec in enumerate(_normalize_specs(specs)):
        if _is_url(spec):
            if downloader is None:
                try:
                    import gdown
                except ImportError as exc:
                    raise ImportError(
                        "Public Drive links require the 'colab' extra: "
                        "pip install mpips[colab]"
                    ) from exc

                def download_with_gdown(
                    url: str, output: Path, is_folder: bool
                ) -> object:
                    if is_folder:
                        return gdown.download_folder(
                            url=url, output=str(output), quiet=False
                        )
                    return gdown.download(url=url, output=str(output), quiet=False)

                downloader = download_with_gdown
            is_folder = "/folders/" in spec
            target = destination_path / f"source-{index:03d}"
            if is_folder:
                target.mkdir(parents=True, exist_ok=True)
                downloader(spec, target, True)
                resolved.extend(target.rglob("*.npz"))
            else:
                target = target.with_suffix(".npz")
                downloader(spec, target, False)
                if target.exists():
                    resolved.append(target)
        else:
            path = Path(spec).expanduser()
            if not path.exists():
                raise SourceResolutionError(f"Input path does not exist: {path}")
            if path.is_dir():
                resolved.extend(path.rglob("*.npz"))
            elif path.suffix.lower() == ".npz":
                resolved.append(path)
            else:
                raise SourceResolutionError(
                    f"Input is not an NPZ file or folder: {path}"
                )

    unique = sorted({path.resolve() for path in resolved})
    if not unique:
        raise SourceResolutionError(
            "No NPZ files were resolved from the supplied inputs"
        )
    return unique
