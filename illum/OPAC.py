#!/usr/bin/env python3

import sys
from collections import OrderedDict

import numpy as np
import toml
from scipy import interpolate

import illum
from illum.pytools import LOP_norm


def ordinal(n):
    return str(n) + {1: "st", 2: "nd", 3: "rd"}.get(n, "th")


def OPAC(wavelengths):
    # READ DATA FROM INPUT FILES
    mie_path = illum.path + "/data/Aerosol_optics/"

    with open("inputs_params.toml") as f:
        params = toml.load(f)
    layer = [aero["profile"] for aero in params["aerosols"]]

    aerosol_types = OrderedDict(
        (
            ("inso", "insoluble aerosol"),
            ("waso", "water soluble aerosol"),
            ("soot", "soot"),
            ("ssam", "sea salt (acc)"),
            ("sscm", "sea salt (coa)"),
            ("minm", "mineral (suc)"),
            ("miam", "mineral (acc)"),
            ("micm", "mineral (coa)"),
            ("mitr", "mineral transported"),
            ("suso", "sulfate droplets"),
            ("fogr", "fog"),
        )
    )
    N_types = len(aerosol_types)

    for contlayer, combination_type in enumerate(layer, 1):
        N = np.zeros(N_types)
        if combination_type.lower() == "manual":
            print(f"Particle concentration of the {ordinal(contlayer)} layer (manual)")
            for i, descr in enumerate(aerosol_types.values()):
                N[i] = float(input(f"Particle concentration of {descr}:"))
        else:
            with open(mie_path + "combination_types") as f:
                combination_types = toml.load(f)
            if combination_type not in combination_types:
                print(
                    "ERROR. Incorret aerosol combination definition. "
                    "See aerosol_guide.txt"
                )
                sys.exit()
            index = list(aerosol_types.keys())
            for k, v in combination_types[combination_type].items():
                N[index.index(k)] = v
        for wl in wavelengths:
            # open files from each aerosol type
            ext_type = np.zeros(N_types)
            scat_type = np.zeros(N_types)
            pf_type = np.zeros((181, N_types))
            for j, type in enumerate(aerosol_types):
                RH = (
                    params["relative_humidity"]
                    if type in ["waso", "ssam", "sscm", "suso"]
                    else 0
                )
                OPAC_filename = f"{mie_path}/OPAC_data/{type}{RH:02}"
                wl_prop = np.genfromtxt(
                    OPAC_filename, skip_header=17, skip_footer=120, comments=None
                )[:, 1:]
                pf_array = np.loadtxt(OPAC_filename)
                scat_angle = pf_array[:, 0]
                pf_array = pf_array[:, 1:].T

                ext_type[j] = np.interp(wl / 1000, wl_prop[:, 0], wl_prop[:, 1])
                scat_type[j] = np.interp(wl / 1000, wl_prop[:, 0], wl_prop[:, 2])
                # cubic interpolation for a given wl and angle
                pf_function = interpolate.interp2d(
                    scat_angle, wl_prop[:, 0], pf_array, kind="cubic"
                )
                # pf function i=angle, j=type
                pf_type[:, j] = pf_function(np.arange(181), wl / 1000)

            # creating the variables of the specific combination of aerosols
            # single scattering albedo
            w_total = np.sum(scat_type * N) / np.sum(ext_type * N)

            # phase function (angle)
            pf_norm = 4 * np.pi * LOP_norm(np.arange(181), np.sum(pf_type * N, 1))
            with open(f"./Inputs/{combination_type}_{wl:g}.txt", "w+") as f:
                f.write(str(w_total) + " # single scatering albedo\n")
                f.write("ScatAngle PhaseFct\n")
                np.savetxt(f, np.stack([np.arange(181), pf_norm], 1), fmt="%g")
