#!/usr/bin/env python

import numpy as np, matplotlib.pyplot as plt, re, os
import subprocess as sub, shutil
from collections import OrderedDict as odict, defaultdict as ddict
from glob import glob
from pytools import *
	
# Load data
# IMPORTANT : x axis of all similar data must be the same

shutil.rmtree("Intrants",True)
shutil.rmtree("Lamps",True)
print "Loading data..."

# Angular distribution (normalised to 1)
lop_files = glob("Lights/*.lop")
angles = np.loadtxt(lop_files[0])[:,1]
lop = { os.path.basename(s).split('_',1)[0]:LOP_norm(angles,np.loadtxt(s)[:,0]) for s in lop_files }

# Spectral distribution (normalised with scotopric vision to 1)
wavelenght, viirs = np.loadtxt("Lights/viirs.dat", skiprows=1).T
scotopic = np.loadtxt("Lights/scotopic.dat", skiprows=1)[:,1]
photopic = np.loadtxt("Lights/photopic.dat", skiprows=1)[:,1]

ratio_ps = float(raw_input("    photopic/scotopic ratio ? (0 <= p/(s+p) <= 1) : "))
norm_spectrum = ratio_ps*photopic + (1-ratio_ps)*scotopic

spct_files = glob("Lights/*.spct")
spct = { os.path.basename(s).split('_',1)[0]:SPD_norm(wavelenght,norm_spectrum,np.loadtxt(s,skiprows=1)[:,1]) for s in spct_files }

# lamps distribution
inv_name = raw_input("    LOP inventory filename : ")
zonData = parse_inventory(inv_name,6)

# make zon file
with open(inv_name) as f:
	zonfile = strip_comments(f.readlines())
zonfile = map(lambda s: s.split()[:6], zonfile)

print "Calculating the generalized lamps..."

# Calculate zones lamps
zones = make_zones(angles, lop, wavelenght, spct, zonData )

print "Saving data..."

dirname = "Lamps"
if not os.path.exists(dirname):
	os.makedirs(dirname)

for i in xrange(len(zones)):
	bin_zon = np.zeros((len(angles)+1,len(wavelenght)+1))
	bin_zon[0,0] = len(wavelenght+1)
	bin_zon[1:,0] = angles
	bin_zon[0,1:] = wavelenght
	bin_zon[1:,1:] = zones[i]

	np.savetxt("Lamps/zone%i_lamp.dat"%(i+1), bin_zon[1:])
	bin_zon.astype(np.float32).tofile("Lamps/zone%i_lamp.bin"%(i+1))

print "Plotting..."

sub.call(["./zones_plot.sh","%d"%len(zones)])

print "Splitting in a few wavelenghts..."
n = int(raw_input("    Number of wavelenghts to use : "))
lmin = float(raw_input("    lambda min : "))
lmax = float(raw_input("    lambda max : "))

bool_array = (lmin<=wavelenght)*(wavelenght<lmax)

limits = np.array(map(np.min,np.array_split(wavelenght[bool_array],n,-1))+[lmax])

filename = "integration_limits.dat"
with open(filename,'w') as f:
	f.write("%d\n"%n)
with open(filename,'ab') as f:
	np.savetxt(f,limits[:,np.newaxis])

# Create the desired lamp files
x = np.mean([limits[1:],limits[:-1]],0)
y = np.array(map(np.mean,np.array_split(zones[:,:,bool_array],n,-1),[-1]*n)).transpose(1,2,0)

print "Creating files..."

for l in xrange(n):
	dirname = "Intrants/"
	if not os.path.exists(dirname):
		os.makedirs(dirname)
	for z in xrange(len(zones)):
		np.savetxt( dirname+"fctem_wl_%03d_zon_%03d.dat"%(x[l],z+1), np.concatenate([ y[z,:,l],angles ]).reshape((2,-1)).T )

ans = raw_input("    Preparing files for viirs2lum ? ([y]/n) ")

stop = False
try:
	if ans[0] in ['N','n']:
		stop = True
except IndexError:
	pass

if not stop:
	out_name = raw_input("Output root name of the experiment [this name will be use d for all the subsequent files]?\n    ")
	pgm_name = raw_input("viirs-dnb file name? [e.g. stable-lights.pgm]\n    ")
	modis_name = raw_input("modis reflectance file list file name? [e.g. modis.dat]\n    ")
	modis_dir = raw_input("modis directory? [e.g. pgms]\n    ")
	zon_name = out_name+".zon"
	srtm_name = raw_input("elevation file name? [e.g. srtm.pgm]\n    ")
	
	dir_name = "./Intrants/"
	tmp_names = {'sat':"stable_lights.pgm", 'modis':"modis.dat", 'viirs':"viirs.dat", 'zon':"zone.zon"}
	tmp_list = set(tmp_names.values())
	tmp_names['integ'] = "integration_limits.dat"
	tmp_names['srtm'] = "srtm.pgm"

	modis_files = np.genfromtxt(modis_name,skiprows=1,usecols=1,dtype=str)
	modis_files = map(lambda s: modis_dir+"/"+s,modis_files)
	zon_files = [ "Lamps/zone%d_lamp.dat" % (i+1) for i in xrange(len(zones)) ]
	for filename in np.concatenate([modis_files,zon_files]):
		name = dir_name+os.path.basename(filename)
		try:
			os.symlink(os.path.abspath(filename),name)
		except OSError as e:
			if e[0] != 17:
				raise
		tmp_list.add(name)

	with open(zon_name,'w') as f:
		f.write("%d\n" % len(zonfile))
		for i in xrange(len(zonfile)):
			zonfile[i].insert(3,os.path.basename(zon_files[i]))
			f.write((("%s\t"*len(zonfile[i]))[:-1]+"\n") % tuple(zonfile[i]))

	os.symlink(os.path.abspath(pgm_name),dir_name+tmp_names['sat'])
	os.symlink(os.path.abspath(modis_name),dir_name+tmp_names['modis'])
	os.symlink(os.path.abspath("Lights/viirs.dat"),dir_name+tmp_names['viirs'])
	os.symlink(os.path.abspath(zon_name),dir_name+tmp_names['zon'])
	os.symlink(os.path.abspath("integration_limits.dat"),dir_name+tmp_names['integ'])
	os.symlink(os.path.abspath(srtm_name),dir_name+tmp_names['srtm'])

	print "Linking mie files..."
	
	mie_pre = raw_input("    Mie file prefix : ")
	illum_dir = sorted([s for s in os.environ['PATH'].split(':') if 'illumina' in s ], key=lambda s:len(s))[0]
	mie_path = illum_dir + "/Aerosol_optical_prop/"
	mie_files = glob(mie_path+"*.mie.out")
	mie_files = { int(s.split('.')[-3][:3]):s for s in mie_files }
	mie_wl = np.asarray(sorted(mie_files.keys()))
	wl2mie = np.asarray([min(mie_wl, key=lambda i: abs(i-j)) for j in x])
	
	for i in xrange(len(wl2mie)):
		name = dir_name+mie_pre.strip('_')+"_0.%03d0um.mie.out"%x[i]
		try:		
			os.symlink(os.path.abspath(mie_files[wl2mie[i]]),name)
		except OSError as e:
			if e[0] != 17:
				raise
#		tmp_list.add(name)
	
ans = raw_input("    Executing viirs2lum ? ([y]/n) ")

stop = False
try:
	if ans[0] in ['N','n']:
		stop = True
except IndexError:
	pass
	
if not stop:
	print "Launching Fortran..."

	os.chdir(dir_name)
	p = sub.Popen("viirs2lum", stdin=sub.PIPE)
        param = out_name+"\n"+os.path.basename(tmp_names['sat'])+"\n"+os.path.basename(tmp_names['zon'])+"\n"
	p.communicate(param)
	
	print "Fortran done."
	
	for filename in tmp_list:
		os.remove(os.path.basename(filename))

	#mie_files = sorted(glob("*.mie.out"))
	
	with open("zon.lst",'w') as zfile:
		zfile.write('\n'.join( map(lambda n:"%03d"%n, xrange(1,len(zones)+1) ))+'\n')
	with open("wav.lst",'w') as zfile:
		zfile.write('\n'.join( map(lambda n:"%03d"%n, x ))+'\n')
  
	os.chdir("..")

print "Done."

