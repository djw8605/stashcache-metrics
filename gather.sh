#!/bin/sh -x

# Copy files with stashcp
#./stashcp -r /osgconnect/public/dweitzel/stashcache-metrics/data ./

#module load python/3.7.0

# Unpack your envvironment (with your packages), and activate it
tar -xzf my_env.tar.gz
#python3 -m venv my_env
#source my_env/bin/activate

# Unpack the data files
tar xzf json_outputs.tar.gz

ls -la

# Run the Python script
export PYTHONPATH=$PWD/my_env
python3 -u gather-working-set.py $1 $2

# Deactivate environment 
deactivate

rm -f *.json

