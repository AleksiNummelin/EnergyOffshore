#!/usr/bin/env python3
#
#Destination Earth: Energy Offshore application preprocessing
#Author: Aleksi Nummelin, Andrew Twelves, Jonni Lehtiranta
#Version: 0.2.3
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
from EnergyOffshore import EnergyOffshore_analysis_and_visualization as EO

if __name__ == '__main__':
    # read a config file with paths
    config     = yaml.load(open('config_visuals.yml'),Loader=yaml.FullLoader)
    path       = config['opa_path']
    outputpath = config['data_path']
    dask_path  = config['dask_path']
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

    # years to process
    years      = list(np.arange(min(config['years']),max(config['years'])))
    #
    for year in years:
        print(year)
        date_axis = pd.date_range(str(year)+"-01-01",str(year)+"-12-31", freq='D')
        if config['preproc']['100ws']:
            # 100 m winds
            winds100m = xr.open_mfdataset(sorted(glob.glob(path+'/'+str(year)+'/'+str(year)+'_*_100ws.nc')),concat_dim='time',
                                      combine='nested',chunks={'time':24},preprocess=EO.preprocess)
            #
            #winds100m = winds100m.rename({'100ws':'ws100'})
            exceed25 = winds100m.ws100.where(winds100m['100ws']>25).notnull().groupby('time.date').sum('time').assign_coords(date=date_axis).expand_dims({'thresholds':np.array([25])})
            #
            for	month in range(1,13):
                timeslice=slice(pd.to_datetime(str(year)+'-'+str(month).zfill(2)+'-01'),pd.to_datetime(str(year)+'-'+str(month).zfill(2)+'-01')+MonthEnd(1))
                filename = str(timeslice.start.year)+'_'+str(timeslice.start.month).zfill(2)+'_'+str(timeslice.start.day).zfill(2)+'_to_'+ \
                    str(timeslice.stop.year)+'_'+str(timeslice.stop.month).zfill(2)+'_'+str(timeslice.stop.day).zfill(2)+'_100ws_timestep_60_daily_thresh_exceed.nc'
                exceed25.squeeze().astype('float32').sel(time=timeslice).to_dataset(name='100ws').to_netcdf(outputpath+filename)
        #
        if config['preproc']['10ws']:
            # 10 m winds
            winds10m  = xr.open_mfdataset(sorted(glob.glob(path+'/'+str(year)+'/*_10ws_raw_data.nc')),concat_dim='time',
                                      combine='nested',chunks={'time':24},preprocess=EO.preprocess)
            #
            #winds10m  = winds10m.rename({'10ws':'ws10'})
            exceed21  = winds10m.ws10.where(winds10m['10ws']>21).notnull().groupby('time.date').sum('time').assign_coords(date=date_axis).expand_dims({'thresholds':np.array([21])})
            #exceed21.astype('float32').to_dataset(name='10ws_exceed21').to_netcdf(outputpath+'10ws_exceed_21_'+str(year)+'.nc')
            exceed18  = winds10m.ws10.where(winds10m['10ws']>18).notnull().groupby('time.date').sum('time').assign_coords(date=date_axis).expand_dims({'thresholds':np.array([18])})
            #exceed18.astype('float32').to_dataset(name='10ws_exceed18').to_netcdf(outputpath+'10ws_exceed_18_'+str(year)+'.nc')
            exceed10  = winds10m.ws10.where(winds10m['10ws']>10).notnull().groupby('time.date').sum('time').assign_coords(date=date_axis).expand_dims({'thresholds':np.array([10])})
            out = xr.concat([exceed10,exceed18,exceed21],dim='thresholds').squeeze()
            for month in range(1,13):
                timeslice=slice(pd.to_datetime(str(year)+'-'+str(month).zfill(2)+'-01'),pd.to_datetime(str(year)+'-'+str(month).zfill(2)+'-01')+MonthEnd(1))
                filename = str(timeslice.start.year)+'_'+str(timeslice.start.month).zfill(2)+'_'+str(timeslice.start.day).zfill(2)+'_to_'+ \
                    str(timeslice.stop.year)+'_'+str(timeslice.stop.month).zfill(2)+'_'+str(timeslice.stop.day).zfill(2)+'_10ws_timestep_60_daily_thresh_exceed.nc'
                out.astype('float32').sel(time=timeslice).to_dataset(name='10ws').to_netcdf(outputpath+filename)
            #exceed10.astype('float32').to_dataset(name='10ws_exceed10').to_netcdf(outputpath+'10ws_exceed_10_'+str(year)+'.nc')
        #
        if config['preproc']['oce']:
            ocean = xr.open_mfdataset(sorted(glob.glob(path+'/'+str(year)+'/*_oce.nc')),concat_dim='time',
                                      combine='nested',chunks={'time':24},preprocess=EO.preprocess)
            ocean = ocean.rename({'time':'date'}).assign_coords(date=date_axis)
            # Sea ice variables
            #
            # see Baltic Ice class rules https://www.finlex.fi/data/normit/47238/03_jaaluokkamaarays_2021_EN.pdf
            # section 4.2.1 on ice loads and the assumed ice thickness at which the different classes can operate
            #
            sithick_exceed005 = (ocean.avg_sithick > 0.05).rename('sithick').expand_dims({'thresholds':np.array([0.05])})
            sithick_exceed04  = (ocean.avg_sithick > 0.4).rename('sithick').expand_dims({'thresholds':np.array([0.4])})
            sithick_exceed06  = (ocean.avg_sithick > 0.6).rename('sithick').expand_dims({'thresholds':np.array([0.6])})
            out = xr.concat([sithick_exceed005,sithick_exceed04,sithick_exceed06],dim='thresholds').squeeze()
            for month in range(1,13):
                timeslice=slice(pd.to_datetime(str(year)+'-'+str(month).zfill(2)+'-01'),pd.to_datetime(str(year)+'-'+str(month).zfill(2)+'-01')+MonthEnd(1))
                filename = str(timeslice.start.year)+'_'+str(timeslice.start.month).zfill(2)+'_'+str(timeslice.start.day).zfill(2)+'_to_'+ \
                    str(timeslice.stop.year)+'_'+str(timeslice.stop.month).zfill(2)+'_'+str(timeslice.stop.day).zfill(2)+'_sithick_timestep_60_daily_thresh_exceed.nc'
                out.astype('float32').sel(time=timeslice).to_dataset(name='sithick').to_netcdf(outputpath+filename)
            #
            siconc_exceed015  = (ocean.avg_siconc  > 0.15).rename('siconc').expand_dims({'thresholds':np.array([0.15])})
            for month in range(1,13):
                timeslice=slice(pd.to_datetime(str(year)+'-'+str(month).zfill(2)+'-01'),pd.to_datetime(str(year)+'-'+str(month).zfill(2)+'-01')+MonthEnd(1))
                filename = str(timeslice.start.year)+'_'+str(timeslice.start.month).zfill(2)+'_'+str(timeslice.start.day).zfill(2)+'_to_'+ \
                    str(timeslice.stop.year)+'_'+str(timeslice.stop.month).zfill(2)+'_'+str(timeslice.stop.day).zfill(2)+'_siconc_timestep_60_daily_thresh_exceed.nc'
                siconc_exceed015.astype('float32').sel(time=timeslice).to_dataset(name='siconc').to_netcdf(outputpath+filename)
            #
            #sithick_exceed005 = (ocean.avg_sithick > 0.05).rename('sithick_exceed0.05').to_dataset().to_netcdf(outputpath+'sithick_exceed_0.05_'+str(year)+'.nc') # our 'no ice' limit# 
            #sithick_exceed04  = (ocean.avg_sithick > 0.4).rename('sithick_exceed0.4').to_dataset().to_netcdf(outputpath+'sithick_exceed_0.4_'+str(year)+'.nc') # IC
            #sithick_exceed06  = (ocean.avg_sithick > 0.6).rename('sithick_exceed0.6').to_dataset().to_netcdf(outputpath+'sithick_exceed_0.6_'+str(year)+'.nc') # IB
            #siconc_exceed015  = (ocean.avg_siconc  > 0.15).rename('siconc_exceed0.15').to_dataset().to_netcdf(outputpath+'siconc_exceed_0.15_'+str(year)+'.nc') # commonly used as the ice edge location
