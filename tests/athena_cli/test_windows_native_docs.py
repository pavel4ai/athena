from pathlib import Path


def test_windows_native_install_path_docs_match_installer() -> None:
    doc = Path("website/docs/user-guide/windows-native.md").read_text()
    install = Path("scripts/install.ps1").read_text()

    # The launchers live in the managed binary dir OUTSIDE the git checkout
    # (ATHENA_HOME\bin, next to the managed uv) — NOT the whole venv\Scripts
    # (which would shadow the user's python, #83797) and NOT a dir inside
    # the checkout (which `athena update`'s autostash swept off disk).
    assert "%LOCALAPPDATA%\\athena\\bin" in doc
    assert (
        "Get-Command athena        # should print "
        "C:\\Users\\<you>\\AppData\\Local\\athena\\bin\\athena.exe"
    ) in doc
    # Installer exposes $AthenaHome\bin, and must copy the launchers into it.
    assert '$athenaBin = "$AthenaHome\\bin"' in install
    assert "athena.exe" in install and "athena-acp.exe" in install
    # Guard against regressions to either legacy layout.
    assert '$athenaBin = "$InstallDir\\venv\\Scripts"' not in install
    assert '$athenaBin = "$InstallDir\\bin"' not in install
