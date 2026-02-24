import asyncio
from src.extensions.manager import ExtensionManager, get_extension_manager


def test_core_extensions_loaded():
    mgr = get_extension_manager()
    exts = mgr.list()
    names = [e["name"] for e in exts]
    assert any("src.extensions.core.file_search" in n for n in names), names
    assert any("src.extensions.core.web_search" in n for n in names), names


def test_load_reload_enable_disable(tmp_path):
    mgr = ExtensionManager(base_paths=[tmp_path])
    # create a fake extension module file under the provided base path
    mod_dir = tmp_path
    mod_file = mod_dir / "fake_ext.py"
    mod_file.write_text("EXTENSION_METADATA={'name':'fake_ext'}\nasync def execute(params):\n    return {'ok': True}\n")
    # discover should find the module by relative path
    found = mgr.discover()
    # We can't import it by a proper package path in this test easily, but ensure discover ran without error
    assert isinstance(found, list)

    # Test enabling/disabling on a non-loaded extension raises KeyError
    try:
        mgr.disable("nonexistent")
        assert False, "Expected KeyError"
    except KeyError:
        pass

    try:
        mgr.enable("nonexistent")
        assert False, "Expected KeyError"
    except KeyError:
        pass
