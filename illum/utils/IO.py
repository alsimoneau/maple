# Functions related to IO opperations
# Author: Alexandre Simoneau

import astropy as _astropy
import astropy.io.fits
import astropy.wcs
import numpy as _np
import rasterio as _rio

# Georeferenced FITS


def load_fits(filename, c=True, gdal_like=False):
    """Loads a FITS file."""
    hdu = _astropy.io.fits.open(filename)[0]
    try:
        wcs = _astropy.wcs.WCS(hdu.header)
    except IndexError:
        return hdu.data, None
    c = wcs.all_pix2world([[-0.5, -0.5], [0.5, 0.5]], 0)
    if gdal_like:
        gt = (c[0, 0], c[1, 0] - c[0, 0], 0, c[0, 1], 0, c[1, 1] - c[0, 1])
    else:
        gt = (c[1, 0] - c[0, 0], 0, c[0, 0], 0, c[1, 1] - c[0, 1], c[0, 1])
    return hdu.data, gt


# GeoTiff


def load_geotiff(filename):
    """Open a georeferenced tiff image as a numpy array.

    Returns the data array, the projection and the geotransform."""
    rst = _rio.open(filename)
    return rst.read(1), rst.crs, rst.get_transform()


def save_geotiff(filename, arr, arr_like=None, **kwargs):
    """Saves a 2D numpy data array as a georeferenced tiff image."""
    if arr_like is not None and type(arr_like is _rio.io.DatasetReader):
        defaults = arr_like.profile
    else:
        defaults = dict(
            count=1,
            nodata=None,
            dtype=str(arr.dtype),
            height=arr.shape[0],
            width=arr.shape[1],
            BIFTIFF="IF_NEEDED",
        )
    defaults.update(kwargs)
    profile = _rio.profiles.DefaultGTiffProfile(**defaults)
    arr = arr.astype(profile["dtype"], copy=False)
    with _rio.open(filename, "w", **profile) as f:
        for idx, window in f.block_windows(1):
            f.write(arr[window.toslices()], 1, window=window)


# Fortran binary files


def load_bin(filename, dtype=_np.float32):
    """Load a ILLUMINA binary file.

    Returns the data as an array."""
    with open(filename) as f:
        shape = _np.fromfile(f, dtype=_np.uint32, count=4)[1:-1][::-1]
        data = _np.fromfile(f, dtype=_np.float32, count=-1)[1::3]
    return data.reshape(shape).astype(dtype)


def save_bin(filename, data):
    """Saves a numpy data array as an ILLUMINA binary file."""
    data = data.astype(_np.float32)
    shape = data.shape[::-1]
    size = data.size
    data_flat = data.flatten()
    filler = _np.ones(size, dtype=_np.float32) * 5.6e-45

    head = _np.array((8,) + shape + (8,)).astype(_np.uint32)
    body = _np.array([filler, data_flat, filler]).T.flatten()

    with open(filename, "w") as f:
        head.tofile(f)
    with open(filename, "a") as f:
        body.tofile(f)