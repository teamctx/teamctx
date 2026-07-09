from __future__ import annotations

import sys

import pytest


def test_missing_mcp_dependency_gets_plain_message(monkeypatch, capsys) -> None:
    for name in [m for m in sys.modules if m == "mcp" or m.startswith("mcp.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.delitem(sys.modules, "teamctx.mcp_server", raising=False)
    monkeypatch.setitem(sys.modules, "mcp", None)

    from teamctx.mcp_entry import main

    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1
    err = capsys.readouterr().err
    assert "pip install 'teamctx[mcp]'" in err


def test_present_dependency_delegates_to_server(monkeypatch) -> None:
    pytest.importorskip("mcp", reason="the delegation test needs the optional mcp extra")
    import teamctx.mcp_entry as entry
    import teamctx.mcp_server as server

    called: list[bool] = []
    monkeypatch.setattr(server, "main", lambda: called.append(True))
    entry.main()
    assert called == [True]
