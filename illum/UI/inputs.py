#!/usr/bin/env python3
#
# Preprocessing for Illumina
#
# Author : Alexandre Simoneau
# modified by Hector Linares for AOD definition
#
# March 2021

import os
import shutil
from glob import glob

import numpy as np
import toml
from scipy.interpolate import griddata

import illum
import illum.AngularPowerDistribution as APD
import illum.MultiScaleData as MSD
import illum.pytools as pt
import illum.SpectralPowerDistribution as SPD
from illum.inventory import from_lamps, from_zones
from illum.OPAC import OPAC


def inputs():

    print("Preparing the inputs for the experiment.")

    dir_name = "Inputs/"
    shutil.rmtree(dir_name, True)
    os.makedirs(dir_name)
    shutil.copy("inputs_params.toml", dir_name + "inputs_params.toml")

    with open("inputs_params.toml") as f:
        params = toml.load(f)

    if params["inventory"]["zones"] and params["inventory"]["lamps"]:

        print("Validating the inventories.")

        lamps = np.loadtxt(params["inventory"]["lamps"], usecols=[0, 1])
        zones = np.loadtxt(params["inventory"]["zones"], usecols=[0, 1, 2])
        zonData = pt.parse_inventory(params["inventory"]["zones"], 7)

        hasLights = [sum(x[0] for x in z) != 0 for z in zonData]

        circles = MSD.from_domain()
        for dat, b in zip(zones, hasLights):
            circles.set_circle((dat[0], dat[1]), dat[2] * 1000, b)

        zones_ind = MSD.from_domain()
        for i, dat in enumerate(zones, 1):
            zones_ind.set_circle((dat[0], dat[1]), dat[2] * 1000, i)

        failed = set()
        for j, coords in enumerate(lamps, 1):
            for i in range(len(circles)):
                try:
                    col, row = circles._get_col_row(coords, i)
                    if circles[i][row, col] and col >= 0 and row >= 0:
                        zon_ind = zones_ind[i][row, col]
                        failed.add((j, coords[0], coords[1], zon_ind))
                except IndexError:
                    continue

        if len(failed):
            for i, lat, lon, zon_ind in sorted(failed):
                print(
                    f"WARNING: Lamp #{i} ({lat:.06g},{lon:.06g}) "
                    f"falls within non-null zone #{zon_ind}"
                )

    if params["viewing_angles"]["road_orientation"]:
        print("Computing road orientation (Can be slow for large domains)")
        from illum.street_orientation import street_orientation

        with open("domain.toml") as f:
            domain_params = toml.load(f)
        srs = domain_params["srs"]
        lats, lons = MSD.from_domain().get_obs_pos()
        bearings = street_orientation(lats, lons, srs)
        np.savetxt(dir_name + "/brng.lst", bearings, fmt="%g")

    print("Loading photometry files.")

    # Angular distribution (normalised to 1)
    def parse_key(fname):
        return os.path.basename(fname).rsplit(".", 1)[0].split("_", 1)[0]

    angles = np.arange(181)
    lop = {
        parse_key(fname): APD.load(fname).normalize().interpolate(step=1)
        for fname in glob("data_files/lop/*")
    }

    # Spectral distribution (normalised with scotopric vision to 1 lm / W)
    norm = SPD.load("data_files/sens/photopic.dat").normalize()
    norm.data *= 683.002
    wav = norm.wavelengths
    viirs = SPD.load("data_files/sens/viirs.dat").interpolate(norm).normalize()

    spct = {
        parse_key(fname): SPD.load(fname).interpolate(norm).normalize(norm)
        for fname in glob("data_files/spct/*")
    }

    print("Splitting in wavelengths bins.")

    if os.path.isfile("spectral_bands.dat"):
        bins = np.loadtxt("spectral_bands.dat", delimiter=",")
        n_bins = bins.shape[0]
    else:
        n_bins = params["wavelengths"]["nb_bins"]
        lmin = params["wavelengths"]["min"]
        lmax = params["wavelengths"]["max"]

        limits = np.linspace(lmin, lmax, n_bins + 1)
        bins = np.stack([limits[:-1], limits[1:]], axis=1)

    bool_array = (wav >= bins[:, 0:1]) & (wav < bins[:, 1:2])
    x = bins.mean(1)
    bw = bins[:, 1] - bins[:, 0]

    print("Interpolating reflectance.")

    aster = {
        parse_key(fname): SPD.load(fname).interpolate(wav)
        for fname in glob("data_files/refl/*")
    }

    sum_coeffs = sum(params["reflectance"][type] for type in params["reflectance"])
    if sum_coeffs == 0:
        sum_coeffs = 1.0

    refl = sum(
        aster[type].data * coeff / sum_coeffs
        for type, coeff in params["reflectance"].items()
    )

    reflect = [np.mean(refl[mask]) for mask in bool_array]

    with open(dir_name + "/refl.lst", "w") as zfile:
        zfile.write("\n".join(["%.06g" % n for n in reflect]) + "\n")

    print("Linking mie files.")

    shutil.copy2(
        os.path.abspath(illum.path + "/data/Molecular_optics/MolecularAbs.txt"),
        dir_name,
    )

    OPAC(x)

    shutil.copy("srtm.hdf5", dir_name)

    with open(dir_name + "/wav.lst", "w") as zfile:
        zfile.write("".join(f"{w:g} {b:g}\n" for w, b in zip(x, bw)))

    if params["inventory"]["zones"]:
        dir_name = ".Inputs_zones/"
        inv_name = params["inventory"]["zones"]
        n_inv = 7
        shutil.rmtree(dir_name, True)
        os.makedirs(dir_name)
        from_zones(
            dir_name,
            inv_name,
            n_inv,
            n_bins,
            params,
            x,
            lop,
            angles,
            wav,
            spct,
            viirs,
            refl,
            bool_array,
        )

    if params["inventory"]["lamps"]:
        dir_name = ".Inputs_lamps/"
        shutil.rmtree(dir_name, True)
        os.makedirs(dir_name)
        from_lamps(
            dir_name,
            n_bins,
            params,
            x,
            lop,
            angles,
            wav,
            spct,
            viirs,
            refl,
            bool_array,
        )
    dir_name = "Inputs/"

    print("Unifying inputs.")

    lfiles = {fname.split(os.sep)[-1] for fname in glob(".Inputs_lamps/*")}
    zfiles = {fname.split(os.sep)[-1] for fname in glob(".Inputs_zones/*")}
    for fname in lfiles - zfiles:
        shutil.move(os.path.join(".Inputs_lamps", fname), "Inputs")
    for fname in zfiles - lfiles:
        shutil.move(os.path.join(".Inputs_zones", fname), "Inputs")
    for fname in zfiles & lfiles:
        if "fctem" in fname:
            shutil.move(os.path.join(".Inputs_lamps", fname), "Inputs")
        elif fname.endswith(".lst"):
            with open(os.path.join(".Inputs_lamps", fname)) as f:
                ldat = f.readlines()
            with open(os.path.join(".Inputs_zones", fname)) as f:
                zdat = f.readlines()
            with open(os.path.join("Inputs", fname), "w") as f:
                f.write("".join(sorted(set(ldat + zdat))))
        elif fname.endswith(".hdf5"):
            ldat = MSD.Open(os.path.join(".Inputs_lamps", fname))
            zdat = MSD.Open(os.path.join(".Inputs_zones", fname))
            for i, dat in enumerate(ldat):
                zdat[i][dat != 0] = dat[dat != 0]
            zdat.save(os.path.join("Inputs", fname))
        else:
            print("WARNING: File %s not merged properly." % fname)
    if "origin.hdf5" not in zfiles:
        origin = MSD.from_domain()
        origin.save("Inputs/origin")
    shutil.rmtree(".Inputs_lamps", True)
    shutil.rmtree(".Inputs_zones", True)

    # Interpolation of the obstacles properties
    defined = MSD.Open(dir_name + "origin.hdf5")
    lights_file = dir_name + "lights.hdf5"
    if os.path.isfile(lights_file):
        lights = MSD.Open(lights_file)
        for i, layer in enumerate(lights):
            defined[i] += layer

    for geo in ["obsth", "obstd", "obstf", "altlp"]:
        geometry = MSD.Open(dir_name + geo + ".hdf5")
        for i, mask in enumerate(defined):
            geometry[i] = (
                griddata(
                    points=np.where(mask),
                    values=geometry[i][mask.astype(bool)],
                    xi=tuple(np.ogrid[0 : mask.shape[0], 0 : mask.shape[1]]),
                    method="nearest",
                )
                if mask.any()
                else np.zeros_like(geometry[i])
            )
        geometry.save(dir_name + geo)

    print("Done.")
