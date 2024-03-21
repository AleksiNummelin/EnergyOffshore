# DT CLIMATE - ENERGY OFFSHORE USE CASE

This is the repository containing the EnergyOffshore Python package (under the EnergyOffshore_package directory) and the scripts that demonstrate their use and reproduce the EnergyOffshore use case output for the use case demonstration deliverable D340.10.5.1.

## Reproducing the deliverable analysis on LUMI

It is best to use the scripts on compute nodes, and getting an interactive shell on LUMI is easiest through the web-interface https://docs.lumi-supercomputer.eu/firststeps/loggingin-webui/

The easiest way to access a nice Python environment on LUMI is creating a singularity container as follows

`singularity pull docker://pangeo/pangeo-notebook:latest (creates a singularity container from a docker container)`

which creates a container pangeo-notebook_latest.sif.

This container can be then activated with 

`singularity shell --bind /pfs/lustrep3/scratch/project_465000454/ pangeo-notebook_latest.sif`

where `--bind /pfs/lustrep3/scratch/project_465000454/` mounts this folder so that it can be used with the singularity shell.

Finally, the EnergyOffshore package can be installed using pip

`pip install EnergyOffshore`

Then the project repository can be cloned with `git clone https://github.com/AleksiNummelin/EnergyOffshore.git` and then the python-scripts within the scripts folder can then be run with e.g.

`python3 run_EnergyOffshore_analysis_and_visualization.py`

The scripts can be controlled using the `config_visuals.yml` YAML file.