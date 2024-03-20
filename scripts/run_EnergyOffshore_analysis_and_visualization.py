#!/usr/bin/env python3
#
#Destination Earth: Energy Offshore application
#Author: Aleksi Nummelin, Andrew Twelves, Jonni Lehtiranta
#Version: 0.1.0

### --- Libraries --- ### 
import numpy as np
import xarray as xr
import glob
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.path as mpath
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import from_levels_and_colors
import yaml
from dask.distributed import Client, LocalCluster, progress
import os
import socket
from EnergyOffshore import EnergyOffshore_analysis_and_visualization as EO

if __name__ == '__main__':
    '''EXECUTE ENERGY OFFSHORE -- STATISTICS IN SUPPORT OF SITING'''
    #
    # load configuration file
    config     = yaml.load(open('config_visuals.yml'),Loader=yaml.FullLoader)
    threshold_combination = config['threshold_combination']
    years_str = str(config['years'][0])+'_'+str(config['years'][1])
    #
    # create a dask cluster if desired
    if config['use_dask']:
        local_dir = config['dask']['dask_path']+socket.gethostname()+'/'
        if not os.path.isdir(local_dir):
            os.system('mkdir -p '+local_dir)
            print('created folder '+local_dir)
        #
        n_workers = config['dask']['n_workers']
        n_threads = config['dask']['n_threads']
        processes = True
        cluster = LocalCluster(n_workers=n_workers,threads_per_worker=n_threads,processes=processes,
                               local_directory=local_dir,lifetime='48 hour',lifetime_stagger='10 minutes',
                               lifetime_restart=True,dashboard_address=None,worker_dashboard_address=None)
        client  = Client(cluster)
    
    ############################
    # LOAD EXCEEDANCE DATA
    # 
    data=EO.load_data(config)
    #
    # COMPUTE MONTHLY CLIMATOLOGIES IF NEEDED
    if config['compute_climatologies']:
        EO.compute_climatologies(data,config)
    
    # LOAD ALL CLIMATOLOGIES FOR PLOTTING
    if config['visualize'] or config['verify']:
        climatology={}
        extreme_climatology={}
        weather_windows={}
        for combination in threshold_combination.keys():
            weather_windows[combination] = xr.open_dataset(config['data_path']+combination+'_weather_windows_years_'+years_str+'.nc')[combination]
            climatology[combination]     = xr.open_dataset(config['data_path']+combination+'_climatology_years_'+years_str+'.nc')[combination]
            extreme_climatology[combination] = xr.open_dataset(config['data_path']+combination+'_extreme_climatology_years_'+years_str+'.nc')[combination]
    
    # VALIDATION WITH CERRA 
    if config['verify']:
        CERRA={}
        for var in config['verification_variables']:
            CERRA[var] = xr.open_dataset(config['data_path']+'CERRA_'+var+'_climatologies.nc')
        # plot some locations
        verification_climatologies={}
        verification_extreme_climatologies={}
        for key in config['verification_variables']:
            if key in ['ws10_exceed10']:
                threshold='Installation_limit_wind'
            elif key in ['ws10_exceed18']:
                threshold='Service_limit_high_wind'
            elif key in ['ws10_exceed21']:
                threshold='Service_limit_storm_wind'
            #
            verification_climatologies['IFS_'+key]           = climatology[threshold]
            verification_extreme_climatologies['IFS_'+key]   = extreme_climatology[threshold]
            verification_climatologies['CERRA_'+key]         = CERRA[key].climatology
            verification_extreme_climatologies['CERRA_'+key] = CERRA[key].extreme_climatology
        #
        EO.verify_climatology_at_location(verification_climatologies,verification_extreme_climatologies,
                                       config['verification_areas'],
                                       plot_name=config['plot_path']+'DT_climate_verify_point_climatologies_with_CERRA.png')
    # VISUALIZE DATA ON A MAP AND TIMESERIES
    if config['visualize']:
        # PLOT A MAP
        central_longitude = sum(config['map']['region'][:2])/2
        central_latitude  = sum(config['map']['region'][2:])/2
        proj2 = ccrs.NearsidePerspective(central_longitude=central_longitude, central_latitude=central_latitude,
                                         satellite_height=config['map']['satellite_height'],
                                         false_easting=0, false_northing=0, globe=None)
        for combination in threshold_combination.keys():
            print('plot '+combination)
            if 'Installation' in combination:
                levels=np.arange(0.1,1,0.1)
            else:
                levels=np.arange(0.5,1,0.05)
            #
            EO.plot_climatology(climatology[combination],weather_windows[combination],config,
                             plot_name=config['plot_path']+'DT_climate_'+combination+'_with_weather_windows.png',
                             plot_windows=True,proj=proj2,extent=config['map']['region'],levels=levels)
            EO.plot_climatology(climatology[combination],weather_windows[combination],config,
                             plot_name=config['plot_path']+'DT_climate_'+combination+'_without_weather_windows.png',
                             plot_windows=False,proj=proj2,extent=config['map']['region'],levels=levels)
        # PLOT A TIMESERIES
        for combination in threshold_combination.keys():
            print('plot '+combination)
            EO.plot_climatology_at_location(climatology[combination],extreme_climatology[combination],
                                         config['timeseries_areas'],
                                         plot_name=config['plot_path']+'DT_climate_'+combination+'_point_climatology.png')

