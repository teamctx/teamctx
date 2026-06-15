from __future__ import annotations

from pathlib import Path

import teamctx

ROOT = Path(__file__).resolve().parent.parent


def test_project_metadata_names_teamctx() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'name = "teamctx"' in pyproject
    assert 'Homepage = "https://teamctx.dev"' in pyproject


def test_product_boundary_is_documented() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    product = (ROOT / "docs/product/product-brief.md").read_text(encoding="utf-8").lower()

    for text in (readme, product):
        assert "no llm" in text
        assert "no agent" in text
        assert "no productivity" in text
        assert "no presence" in text


def test_package_version_is_defined() -> None:
    assert teamctx.__version__ == "0.0.0"

