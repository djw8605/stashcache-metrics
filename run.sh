#!/bin/bash


#!/bin/bash

# Load Python
# (should be the same version used to create the virtual environment)
module load python/3.7.0

# Unpack your envvironment (with your packages), and activate it
tar -xzf my_env.tar.gz
python3 -m venv my_env
source my_env/bin/activate

# Run the Python script 
python3 gather-working-set.py $1 $2

# Deactivate environment 
deactivate

