#!/usr/bin/env python3
#
#Destination Earth: Energy Offshore application preprocessing
#Author: Aleksi Nummelin, Andrew Twelves, Jonni Lehtiranta
#Version: 0.1.0
#
# assumied to be run on LUMI with
# singularity shell --bind /pfs/lustrep3/scratch/project_465000454/ pangeo-notebook_latest.sif
import xarray as xr
import pandas as pd
import numpy as np
import glob
import yaml
#
from dask.distributed import Client, LocalCluster, progress
import os
import socket

def preprocess(ds):
    '''
    Preprocess a dataset checking for variable 'valid_time' and drop it if found

    Input:
    ------
    ds: xarray.Dataset

    Output:
    -------
    ds: xarray.Dataset without the variable 'valid_time'
    '''

    if 'valid_time' in list(ds.variables):
        return ds.drop_vars(['valid_time'])
    else:
        return ds

if __name__ == '__main__':
    #
    dask_path = '/pfs/lustrep3/scratch/project_465000454/nummelin/dask/'
    # create a dask cluster
    local_dir = dask_path+socket.gethostname()+'/'
    if not os.path.isdir(local_dir):
        os.system('mkdir -p '+local_dir)
        print('created folder '+local_dir)
    #
    n_workers = 2
    n_threads = 2
    processes = True
    cluster = LocalCluster(n_workers=n_workers,threads_per_worker=n_threads,processes=processes,
                                            local_directory=local_dir,lifetime='48 hour',lifetime_stagger='10 minutes',
                                            lifetime_restart=True,dashboard_address=None,worker_dashboard_address=None)
    client  = Client(cluster)

    # read a config file with paths
    config     = yaml.load(open('config_visuals.yml'),Loader=yaml.FullLoader)
    path       = config['opa_path']
    outputpath = config['data_path']
    years      = list(np.arange([min(config['years']),max(config['years'])]))
    #
    for year in years:
        print(year)
        date_axis = pd.date_range(str(year)+"-01-01",str(year)+"-12-31", freq='D')
        # 100 m winds
        winds100m = xr.open_mfdataset(sorted(glob.glob(path+'/'+str(year)+'/'+str(year)+'_*_100ws.nc')),concat_dim='time',
                                      combine='nested',chunks={'time':24},preprocess=preprocess)
        #
        winds100m = winds100m.rename({'100ws':'ws100'})
        exceed25 = winds100m.ws100.where(winds100m.ws100>25).notnull().groupby('time.date').sum('time').assign_coords(date=date_axis)
        #
        exceed25.squeeze().astype('float32').to_dataset(name='ws100_exceed25').to_netcdf(outputpath+'ws100_exceed_25_'+str(year)+'.nc')
        #
        # 10 m winds
        winds10m  = xr.open_mfdataset(sorted(glob.glob(path+'/'+str(year)+'/*_10ws_raw_data.nc')),concat_dim='time',
                                      combine='nested',chunks={'time':24},preprocess=preprocess)
        #
        winds10m  = winds10m.rename({'10ws':'ws10'})
        exceed21  = winds10m.ws10.where(winds10m.ws10>21).notnull().groupby('time.date').sum('time').assign_coords(date=date_axis)
        exceed21.astype('float32').to_dataset(name='ws10_exceed21').to_netcdf(outputpath+'ws10_exceed_21_'+str(year)+'.nc')
        exceed18  = winds10m.ws10.where(winds10m.ws10>18).notnull().groupby('time.date').sum('time').assign_coords(date=date_axis)
        exceed18.astype('float32').to_dataset(name='ws10_exceed18').to_netcdf(outputpath+'ws10_exceed_18_'+str(year)+'.nc')
        exceed10  = winds10m.ws10.where(winds10m.ws10>10).notnull().groupby('time.date').sum('time').assign_coords(date=date_axis)
        exceed10.astype('float32').to_dataset(name='ws10_exceed10').to_netcdf(outputpath+'ws10_exceed_10_'+str(year)+'.nc')
        #
        ocean = xr.open_mfdataset(sorted(glob.glob(path+'/'+str(year)+'/*_oce.nc')),concat_dim='time',
                                  combine='nested',chunks={'time':24},preprocess=preprocess)
        ocean = ocean.rename({'time':'date'}).assign_coords(date=date_axis)
        # Sea ice variables
        #
        # see Baltic Ice class rules https://www.finlex.fi/data/normit/47238/03_jaaluokkamaarays_2021_EN.pdf
        # section 4.2.1 on ice loads and the assumed ice thickness at which the different classes can operate
        #
        sithick_exceed005 = (ocean.avg_sithick > 0.05).rename('sithick_exceed005').to_dataset().to_netcdf(outputpath+'sithick_exceed_005_'+str(year)+'.nc') # our 'no ice' limit 
        sithick_exceed04  = (ocean.avg_sithick > 0.4).rename('sithick_exceed04').to_dataset().to_netcdf(outputpath+'sithick_exceed_04_'+str(year)+'.nc') # IC
        sithick_exceed06  = (ocean.avg_sithick > 0.6).rename('sithick_exceed06').to_dataset().to_netcdf(outputpath+'sithick_exceed_06_'+str(year)+'.nc') # IB
        siconc_exceed015  = (ocean.avg_siconc  > 0.15).rename('siconc_exceed015').to_dataset().to_netcdf(outputpath+'siconc_exceed_015_'+str(year)+'.nc') # commonly used as the ice edge location
