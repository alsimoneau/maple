from subprocess import check_output

from setuptools import setup

import illum

gdal_version = (
    check_output(["gdalinfo", "--version"]).decode().split(",")[0].split()[1]
)

setup(
    name="illum",
    version=illum.__version__,
    packages=["illum"],
    install_requires=[
        "astropy",
        "Click",
        "fiona",
        "gdal==" + gdal_version,
        "geopandas",
        "GitPython",
        "h5py",
        "matplotlib",
        "numpy",
        "osmnx",
        "pandas",
        "pillow",
        "progressbar2",
        "pyproj",
        "pyyaml",
        "scipy",
    ],
    extras_require={
        "dev": [
            "black",
            "flake8",
            "ipython",
            "isort",
        ],
    },
    entry_points="""
        [console_scripts]
        illum=illum.main:illum
    """,
)
