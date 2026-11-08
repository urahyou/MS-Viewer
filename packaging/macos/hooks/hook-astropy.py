"""Collect runtime Astropy modules without importing optional visualization/test packages.

The upstream hook imports every submodule, including wcsaxes, whose test-only
pytest.importorskip('matplotlib') raises during collection in our lean environment.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata


def runtime_module(name):
    return (
        ".tests" not in name
        and not name.startswith("astropy.visualization")
        and not name.endswith(".conftest")
    )


datas = collect_data_files("astropy", excludes=["**/tests/**", "**/visualization/**"])
datas += collect_data_files("astropy_iers_data")
datas += copy_metadata("astropy") + copy_metadata("numpy")
datas += [
    (path, target)
    for path, target in collect_data_files("astropy", include_py_files=True)
    if path.endswith(("_parsetab.py", "_lextab.py"))
]
hiddenimports = collect_submodules("astropy", filter=runtime_module)
hiddenimports += ["numpy.lib.recfunctions"]
