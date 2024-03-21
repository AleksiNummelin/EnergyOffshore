# DT CLIMATE - ENERGY OFFSHORE USE CASE

This is a python package used in the Destination Earth: Digital Twin of Climate simulations
project to produce a set of statistics in support of offshore wind
farm siting and long term operations. It includes functions for calculating monhtly mean climatologies, monhtly extreme climatologies (includes interannual variability), monhtly weather window climatologies (frequency of suitable conditions to exist)

## Installation

After installing the dependencies: Xarray, Dask, Distributed, Matplotlib, Cartopy, and, Numpy

The package can be installed using

`pip install EnergyOffshore`

## Usage

Import using

`from EnergyOffshore import EnergyOffshore_analysis_and_visualization as EO`

which allows using functions as `EO.function_name(function_inputs)`


## API content

The package includes the following functions

```

FUNCTIONS
    compute_climatologies(data, config)
        Compute monthly climatologies and save them to netcdf files.

        Input:
	-------
	config: dict, loaded from the configuration.yml file and including
                the names of the desired variables under the key {'var_exceed'}
                and their desired exceedance values. Climatological output
                will be saved under the directory defined by 'data_path' key.

        data:   dict of xr.DataArrays (time,lat,lon). The xr.DataArrays are the daily exceedance
                statistics of a given variable (1-24 if based on hourly data, 0-1 if based on daily data).
                The dict entries are names like 'var_name_exceed_limit' e.g. ws10_exceed_21 for 10 m wind
                exceeding 21 m/s.
        
        Output:
        -------
            
        This function does not return any variables, but instead will save monthly statistics to annual files
        under the directory defined in configuration yml file by the 'data_path' key. 
    
    compute_extreme_climatology(var, quantiles=[0.05, 0.5, 0.95])
        Calculate interannual extemes for each month assuming
        that input array is monthly data
        
        Input:
        ------
        var:       xr.DataArray (time, lat, lon), timeseries of data at any sub-monthly frequency.
        quantiles: List or Array (default=[0.05,0.5,0.95]), specifying the quantiles of interannual variability [0-1]
        
        Output:
        -------
        var_out:   xarray.DataArray (month,lat,lon,quantile), output climatology with quantiles specifying the range of interannual variability
    
    compute_weather_windows(suitable_conditions, windows=[3, 5, 7])
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
    
    load_data(config)
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
    
    plot_climatology(climatology, weather_windows, config, plot_name='DT_climate_threshold_exceedance_with_weather_windows.png', plot_windows=True, proj=None, extent=Non
e, levels=None)
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
    
    plot_climatology_at_location(climatology, extreme_climatology, areas, plot_name)
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
    
    preprocess(ds)
        Preprocess a dataset checking for variable 'valid_time' and drop it if found
        
        Input:
        ------
        ds: xarray.Dataset
        
        Output:
        -------
        ds: xarray.Dataset without the variable 'valid_time'
    
    verify_climatology_at_location(climatologies, extreme_climatologies, areas, plot_name)
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
        Does not return variables, but produces a figure in user defined location (plot_name)\

```