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

def compute_weather_windows(suitable_conditions,windows=[3,5,7]):
    '''
    Determine how likely it is that in a given month
    one will find a weather window (user defined criteria)

    Input:
    ----------
    suitable_conditions: xr.DataArray [time,lat,lon], mask [0 or 1]
                         of suitable conditions that match user 
                         defined criteria (float)
    windows: list or numpy.array, weather window lengths in days (int)
    
    Output:
    ----------
    weather_window: xarray.DataArray (month,lat,lon,window), mean monthly likelihood [0-1]
                    of being within the user defined criteria (i.e. not exceeding the criteria) 
    '''
    for w,window in enumerate(windows):
        # returns 1 if conditions are suitable throughout the time period
        weather_window = suitable_conditions.rolling(time=window,center=True).mean()
        if w==0:
            # return the mean i.e.
            # 'fraction of days (time) in a month' during which there
            # is a weather window corresponding to the given conditions
            # 
            weather_windows=weather_window.where(weather_window==1).fillna(0).\
                groupby('time.month').mean().expand_dims(dim='windows')
        else:
            dum = weather_window.where(weather_window==1).fillna(0).\
                groupby('time.month').mean().expand_dims(dim='windows')
            weather_windows = xr.concat([weather_windows, dum],dim='windows')
    #
    return weather_windows.assign_coords({'windows':windows})

def plot_climatology_at_location(climatology,extreme_climatology,areas,plot_name):
    '''
    Make a climatological plot of given variable at a location. 

    Input:
    ------
    climatology: xr.DataArray [time,lat,lon], mean climatology of a given 'suitable condition'
    extreme_climatology: xr.DataArray [time,lat,lon,quantile], 
                         interannual extreme climatology of a given 'suitable condition'.
                         Quantiles are assumed to include [0.05,0.5,0.95].
    
    areas: dict, {area: {'name':'long_name_of_the_area'
                         'lon_slice':[lon_min,lon_max]
                         'lat_slice':[lat_min,lat_max]
                 }}
    plot_name: str, define the name of the plot (including the path)    

    Output:
    -------
    
    Does not return variables, but produces a figure in user defined location (plot_name)
    '''
    fig,axes = plt.subplots(sharex=True,sharey=True,nrows=len(areas.keys()),ncols=1,figsize=(10,len(areas.keys())*4))
    for a, area in enumerate(areas.keys()):
        if len(areas.keys())>1:
            ax=axes.flatten()[a]
        else:
            ax=axes
        # define area
        lon_slice=slice(min(areas[area]['lon_slice']),max(areas[area]['lon_slice']))
        lat_slice=slice(min(areas[area]['lat_slice']),max(areas[area]['lat_slice']))
        # weight by cos latitude
        w = np.cos(np.radians(extreme_climatology.lat.sel(lat=lat_slice)))
        #
        ax.set_title(areas[area]['name'],fontsize=16)
        ax.fill_between(extreme_climatology.month,
                        (extreme_climatology.sel(quantile=0.05,lon=lon_slice,lat=lat_slice).mean('lon')*w).sum('lat')/w.sum('lat'),
                        (extreme_climatology.sel(quantile=0.95,lon=lon_slice,lat=lat_slice).mean('lon')*w).sum('lat')/w.sum('lat'),
                        color='C1',alpha=0.5)
        l1,=ax.plot(extreme_climatology.month,
                    (extreme_climatology.sel(quantile=0.5,lon=lon_slice,lat=lat_slice).mean('lon')*w).sum('lat')/w.sum('lat'),label='Median',
                    color='C1',lw=2)
        l2,=ax.plot(climatology.month,(climatology.sel(lon=lon_slice,lat=lat_slice).mean('lon')*w).sum('lat')/w.sum('lat'),label='Mean',
                    color='C0',lw=2)
        ax.set_ylim(0,1)
        ax.set_xlim(1,12)
        if a==0:
            ax.legend(fontsize=16)
    #
    ax.set_xlabel('Time [months]',fontsize=18)
    ylab=fig.text(0.06,0.5,'Fraction of days in a month within a threshold [0-1]',fontsize=18,ha='center',va='center',rotation='vertical')
    fig.savefig(plot_name,dpi=300,transparent=True,
                bbox_inches='tight',bbox_extra_artists=[ylab])
    plt.close('all')

def verify_climatology_at_location(climatologies,extreme_climatologies,areas,plot_name):
    '''
    Produce a climatology comparing the model output to reanalysis
    
    Input:
    ------
    climatologies: dict of xr.DataArray [time,lat,lon], mean climatologies of a given 'suitable condition'.
                   dict entries are the different conditions for a given model.
    extreme_climatologies: dict xr.DataArray [time,lat,lon,quantile],
                         interannual extreme climatology of a given 'suitable condition'.
                         Quantiles are assumed to include [0.05,0.5,0.95].
                         dict entries are the different conditions for a given model.
    areas: dict, {area: {'name':'long_name_of_the_area'
                         'lon_slice':[lon_min,lon_max]
                         'lat_slice':[lat_min,lat_max]
                 }}.
                 Climatologies will be averaged over these areas.
    plot_name: str, define the name of the plot (including the path)

    Output:
    -------
    Does not return variables, but produces a figure in user defined location (plot_name)
    '''
    fig,axes = plt.subplots(sharex=True,sharey=True,nrows=len(areas.keys()),ncols=1,figsize=(10,len(areas.keys())*4))
    for a, area in enumerate(areas.keys()):
        if len(areas.keys())>1:
            ax=axes.flatten()[a]
        else:
            ax=axes
        #
        lon_slice=slice(min(areas[area]['lon_slice']),max(areas[area]['lon_slice']))
        lat_slice=slice(min(areas[area]['lat_slice']),max(areas[area]['lat_slice']))
        #
        ax.set_title(areas[area]['name'],fontsize=16)
        for k,key in enumerate(climatologies.keys()):
            if 'ws10_exceed10' in key:
                threshold='Installation_limit_wind'
            elif 'ws10_exceed18' in key:
                threshold='Service_limit_high_wind'
            elif 'ws10_exceed21' in key:
                threshold='Service_limit_storm_wind'
            if 'IFS' in key:
                threshold=threshold+' IFS'
            elif 'CERRA' in key:
                threshold=threshold+' CERRA'
            #
            w = np.cos(np.radians(extreme_climatologies[key].lat.sel(lat=lat_slice)))
            ax.fill_between(extreme_climatologies[key].month,
                            (extreme_climatologies[key].sel(quantile=0.05,lon=lon_slice,lat=lat_slice).mean('lon')*w).sum('lat')/w.sum('lat'),
                            (extreme_climatologies[key].sel(quantile=0.95,lon=lon_slice,lat=lat_slice).mean('lon')*w).sum('lat')/w.sum('lat'),
                            color='C'+str(k),alpha=0.4)
            l1,=ax.plot(extreme_climatologies[key].month,
                        (extreme_climatologies[key].sel(quantile=0.5,lon=lon_slice,lat=lat_slice).mean('lon')*w).sum('lat')/w.sum('lat'),
                         label=threshold,
                        color='C'+str(k),lw=2)
        #
        ax.set_ylim(0,1)
        ax.set_xlim(1,12)
        if a==0:
            ax.legend(fontsize=12)
    #
    ax.set_xlabel('Time [months]',fontsize=18)
    ylab=fig.text(0.06,0.5,'Fraction of days in a month within a threshold [0-1]',fontsize=18,ha='center',va='center',rotation='vertical')
    fig.savefig(plot_name,dpi=300,transparent=True,
                bbox_inches='tight',bbox_extra_artists=[ylab])
    plt.close('all')

def plot_climatology(climatology,weather_windows,
                     plot_name='DT_climate_threshold_exceedance_with_weather_windows.png',
                     plot_windows=True,proj=None,extent=None,levels=None):
    '''
    Plot the climatological frequencies of 'suitable conditions' on a map with/without weather windows
    using matplotlib and cartopy.
    
    Input:
    -------
    climatology:     xr.DataArray [time,lat,lon], mean climatology of a given 'suitable condition'
    weather_windows: xarray.DataArray (month,lat,lon,window), mean monthly likelihood [0-1]
                     of being within the user defined criteria (i.e. not exceeding the criteria)
    plot_name:       str, define the name of the plot (including the path)
    plot_windows:    boolean, whether to include weather_window contours on the map (default=True)
    proj:            cartopy map projection (default=None), if not given NearSidePespective centered on
                     northern Europe will be used.
    extent:          list or array [lon_min,lon_max,lat_min,lat_max] (default=None), 
                     if not None will be used to clip the extent of the map (no effect if None)
    
    Output:
    -------
    Does not return variables, but produces a figure in user defined location (plot_name)
    '''
    #
    if np.any(levels==None):
        levels=np.arange(0.5,1,0.05)
    cmap0=plt.get_cmap('viridis')
    cmlist=[];
    for cl in np.linspace(0,252,len(levels)+1): cmlist.append(int(cl))
    cmap2, norm2 = from_levels_and_colors(levels,cmap0(cmlist),extend='both');
    #
    RIVERS_50m = cfeature.NaturalEarthFeature('physical','rivers_lake_centerlines', '50m',
                                          edgecolor=cfeature.COLORS['water'],
                                          facecolor='none')
    LAND = cfeature.NaturalEarthFeature('physical', 'land', '10m',edgecolor='None', facecolor='lightgrey', zorder=3)
    if proj==None:
        proj = ccrs.NearsidePerspective(central_longitude=15.0, central_latitude=55.0, satellite_height=300E3,
                                        false_easting=0, false_northing=0, globe=None)
    #
    lat = climatology.lat
    lon = climatology.lon
    grid = xr.merge([lat.rename({'lat':'y'}),lon.rename({'lon':'x'}),
                 xr.DataArray(np.arange(lat.min()-0.5*lat.diff('lat').median(),
                                        lat.max()+lat.diff('lat').median(),
                                        lat.diff('lat').median()),dims=('y_b')).rename('lat_b'),
                 xr.DataArray(np.arange(lon.min()-0.5*lon.diff('lon').median(),
                                        lon.max()+lon.diff('lon').median(),
                                        lon.diff('lon').median()),dims=('x_b')).rename('lon_b')])
    #
    fig,axes = plt.subplots(nrows=4,ncols=3,figsize=(3*5,4*5),subplot_kw={'projection':proj})
    for a,ax in enumerate(axes.flatten()):
        ax.set_title('Month:'+str(a+1).zfill(2),fontsize=16)
        cm1=ax.pcolormesh(grid.lon_b,grid.lat_b, climatology.isel(month=a), #data.avg_tos.squeeze()-273.15,                   
                      cmap=cmap2,norm=norm2,
                      transform=ccrs.PlateCarree(),rasterized=True)
        if plot_windows:
            for w in range(weather_windows.windows.size):
                ax.contour(lon,lat,weather_windows.isel(month=a,windows=w),transform=ccrs.PlateCarree(),
                           colors=['red','k','gray'][w],levels=[0.5],linewidths=0.5)
        ax.add_feature(RIVERS_50m,zorder=4)
        ax.add_feature(LAND,zorder=3)
        ax.coastlines(resolution='10m',color='k',linewidth=0.5)
        for tarea in config['timeseries_areas'].keys():
            x0=min(config['timeseries_areas'][tarea]['lon_slice'])
            y0=min(config['timeseries_areas'][tarea]['lat_slice'])
            dx=config['timeseries_areas'][tarea]['lon_slice'][1]-config['timeseries_areas'][tarea]['lon_slice'][0]
            dy=config['timeseries_areas'][tarea]['lat_slice'][1]-config['timeseries_areas'][tarea]['lat_slice'][0]
            ax.add_patch(mpatches.Rectangle(xy=[x0, y0], width=dx, height=dy,
                                            facecolor='none', edgecolor='r',
                                            transform=ccrs.PlateCarree()))
        if extent!=None:
            xlim=extent[:2]
            ylim=extent[2:]
            rect = mpath.Path([[xlim[0], ylim[0]],
                   [xlim[1], ylim[0]],
                   [xlim[1], ylim[1]],
                   [xlim[0], ylim[1]],
                   [xlim[0], ylim[0]],
                   ]).interpolated(20)
            proj_to_data = ccrs.PlateCarree()._as_mpl_transform(ax) - ax.transData
            rect_in_target = proj_to_data.transform_path(rect)
            ax.set_boundary(rect_in_target)
            #ax.set_extent(extent,crs=ccrs.PlateCarree())
        
    cax  = fig.add_axes([0.95,0.15,0.03,0.7])
    cbar = plt.colorbar(mappable=cm1,cax=cax,orientation='vertical')
    clab = cbar.ax.set_ylabel(r'Mean fraction of days in a month within a threshold [0-1]',fontsize=22)
    #
    fig.subplots_adjust(wspace=0.05,hspace=0.025)
    fig.savefig(plot_name,dpi=300,transparent=True,
                bbox_inches='tight',bbox_extra_artists=[clab])
    plt.close('all')

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

def compute_extreme_climatology(var,quantiles=[0.05,0.5,0.95]):
    '''
    Calculate interannual extemes for each month assuming
    that input array is monthly data

    Input:
    ------
    var:       xr.DataArray (time, lat, lon), timeseries of data at any sub-monthly frequency.
    quantiles: List or Array (default=[0.05,0.5,0.95]), specifying the quantiles of interannual variability [0-1]
    
    Output:
    -------
    var_out:   xarray.DataArray (month,lat,lon,quantile), output climatology with quantiles specifying the range of interannual variability
    '''
    # define which indices belong to which month
    month_groups=var.groupby('time.month').groups
    # loop over the months calculating the monthly means and their interannul variability
    for month in month_groups.keys():
        if month==1:
            var_out = var.isel(time=month_groups[month]).groupby('time.year').mean().quantile(quantiles,dim='year').expand_dims({'month':[month]})
        else:
            dum = var.isel(time=month_groups[month]).groupby('time.year').mean().quantile(quantiles,dim='year').expand_dims({'month':[month]})
            var_out = xr.concat([var_out,dum],dim='month')
    
    return var_out

def compute_climatologies(data,config):
    '''
    Compute monthly climatologies and save them to netcdf files.
    
    data: dict of 
    '''
    threshold_combination = config['threshold_combination']
    #
    suitable_conditions={}
    for combination in threshold_combination.keys():
        print(combination)
        for v,var in enumerate(threshold_combination[combination]):
            if 'ws' in var:
                dum = data[var][var]
                dum = (1-dum.where(dum<1).fillna(1)).astype(bool)
            else:
                dum=(1-data[var][var].fillna(1).astype(bool))
            if v==0:
                suitable_conditions[combination] = dum
            else:
                suitable_conditions[combination] = (suitable_conditions[combination] & dum)
        # calculate and save the climatology of weather windows given the 'suitable conditions' mask
        years_str = str(config['years'][0])+'_'+str(config['years'][1])
        print('weather windows')
        weather_window=compute_weather_windows(suitable_conditions[combination].astype('float32').chunk({'lat':60,'lon':60}))
        weather_window.to_dataset(name=combination).\
            to_netcdf(config['data_path']+combination+'_weather_windows_years_'+years_str+'.nc')
        # calculate and save the climatology of the suitable conditions (frequency)
        print('climatology')
        suitable_climatology=suitable_conditions[combination].astype('float32').groupby('time.month').mean().chunk({'lat':60,'lon':60})
        suitable_climatology.to_dataset(name=combination).\
            to_netcdf(config['data_path']+combination+'_climatology_years_'+years_str+'.nc')
        # calculate and save the extreme (interannual) climatology of suitable weather windows (frequency during worse/median/best year)
        print('extreme climatology')
        suitable_extreme_climatology = compute_extreme_climatology(suitable_conditions[combination].astype('float32').chunk({'time':-1,'lat':60,'lon':60}))
        suitable_extreme_climatology.to_dataset(name=combination).\
            to_netcdf(config['data_path']+combination+'_extreme_climatology_years_'+years_str+'.nc')


def load_data(config):
    '''
    Load data give the config dictionary

    Input:
    ------
    config: dict, loaded from the configuration.yml file and including
            the names of the desired variables under the key {'var_exceed'} 
            and their desired exceedance values.  
    
    Output:
    -------
    data: dict of xr.DataArrays (time,lat,lon). The xr.DataArrays are the daily exceedance
          statistics of a given variable (1-24 if based on hourly data, 0-1 if based on daily data).
          The dict entries are names like 'var_name_exceed_limit' e.g. ws10_exceed_21 for 10 m wind
          exceeding 21 m/s.
    '''
    var_exceed = config['var_exceed']
    #
    year0=config['years'][0]
    year1=config['years'][1]
    data={}
    for var in var_exceed.keys():
        print(var)
        for limit in var_exceed[var]['limits']:
            flist=[]
            for year in range(year0,year1+1):
                flist.append(config['data_path']+var+'_exceed_'+limit+'_'+str(year)+'.nc')
            data[var+'_exceed'+limit] = xr.open_mfdataset(flist,combine='nested',
                                                          concat_dim='date',preprocess=preprocess,engine='netcdf4')
            if 'date' in list(data[var+'_exceed'+limit].coords):
                print(var+'_exceed'+limit)
                data[var+'_exceed'+limit]=data[var+'_exceed'+limit].rename({'date':'time'})
    return data
