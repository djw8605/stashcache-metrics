
#from elasticsearch_dsl import Search, A
from opensearchpy import Search, A, OpenSearch
#from elasticsearch import Elasticsearch
from datetime import datetime, timedelta
import dateutil
import json
import os
import glob
import pandas as pd
from multiprocessing import Pool
import sys

def connect_elastic():
    client = OpenSearch(
        ['https://gracc.opensciencegrid.org/q'],
        timeout=600, use_ssl=True, verify_certs=False)
    return client

working_files = {}

def gather_data(from_date, to_date, client):
    print(f"Searching for data from {from_date} to {to_date}")
    index = "xrd-stash*"
    #from_date = datetime.datetime.now() - datetime.timedelta(days=365)
    #from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0, day=1)
    #to_date = datetime.datetime.now()
    s = Search(using=client, index=index)
    s = s.filter('range', **{'@timestamp': {'from': from_date, 'to': to_date }})

    def scan_aggs(search, source_aggs, size=10):
        """
        Helper function used to iterate over all possible bucket combinations of
        ``source_aggs``.  Uses the ``composite`` aggregation under the hood to perform this.
        """
        def run_search(**kwargs):
            s = search[:0]
            curBucket = s.aggs.bucket('comp', 'composite', sources=source_aggs, size=size, **kwargs)
            #for term in new_unique_terms:
            #    curBucket = curBucket.bucket(term[0], 'terms', field=term[0], missing=term[1], size=(2**31)-1)
            for metric in metrics:
                curBucket.metric(metric[0], metric[1], field=metric[0], missing=metric[2])
            return s.execute()

        response = run_search()
        while response.aggregations.comp.buckets:
            for b in response.aggregations.comp.buckets:
                yield b
            if 'after_key' in response.aggregations.comp:
                after = response.aggregations.comp.after_key
            else:
                after= response.aggregations.comp.buckets[-1].key
            response = run_search(after=after)

    composite_buckets = []
    composite_buckets.append({'filename': A('terms', field='filename.keyword', missing_bucket=False)})
    metrics = [
        ['filesize', 'max', 0],
        ['read', 'sum', 0]
    ]
    response = scan_aggs(s, composite_buckets, size=1000)


    #curBucket = s.aggs.bucket('filename', 'terms', field='filename.keyword', size=(2**31)-1)
    #curBucket.metric('filesize', 'max', field='filesize')
    #curBucket.metric('read', 'sum', field='read')
    #print(s.to_dict())

    #response = s.execute()
    #if not response.success():
    #    print(response.to_dict())
    #    return response.success()
    for file_attr in response:
        filename = file_attr['key']['filename']
        if filename in working_files:
            working_files[filename]['read'] += file_attr['read']['value']
        else:
            working_files[filename] = {
                'read': file_attr['read']['value'],
                'filesize': file_attr['filesize']['value']
            }
        #print(file_attr.to_dict())
    return True

def map_paths(old_files):

    new_files = {}
    for filename in old_files:
        
        dirname1 = "/".join(filename.split('/', 2)[:2])
        dirname2 = "/".join(filename.split('/', 3)[:3])
        if filename.startswith('/user'):
            new_filename = dirname2
        elif filename.startswith('/pnfs/fnal.gov/usr'):
            new_filename = "/".join(filename.split('/')[:5])
        elif filename.startswith('/gwdata'):
            new_filename = dirname2
        elif filename.startswith('/chtc/'):
            new_filename = '/chtc'
        elif filename.startswith('/icecube/'):
            new_filename = '/icecube'
        elif filename.startswith('/osgconnect/'):
            new_filename = "/".join(filename.split('/')[:4])
        elif filename.startswith('/merra2/'):
            new_filename = '/merra2'
        elif filename.startswith('/jlab'):
            new_filename = "/".join(filename.split('/')[:3])
        elif filename.startswith('/gluex'):
            new_filename = '/gluex'
        elif filename.startswith('/hcc'):
            new_filename = "/".join(filename.split('/')[:6])
        elif filename.startswith('/ospool/PROTECTED'):
            new_filename = "/".join(filename.split('/')[:4])
        elif filename.startswith('/ospool'):
            new_filename = "/".join(filename.split('/')[:5])
        elif filename.startswith('/nrp/protected'):
            new_filename = "/".join(filename.split('/')[:4])
        elif filename.startswith('/nrp'):
            new_filename = "/".join(filename.split('/')[:3])
        elif filename.startswith('/knightlab'):
            new_filename = '/knightlab'
        elif filename.startswith('/igwn'):
            new_filename = "/".join(filename.split('/')[:3])
        elif filename.startswith('/et-gw'):
            new_filename = "/".join(filename.split('/')[:3])
        elif filename.startswith('/path-facility/data'):
            new_filename = "/".join(filename.split('/')[:4])


        else:
            print("Not found: {}".format(dirname2))
            continue
        
        if new_filename in new_files:
            new_files[new_filename]['read'] += old_files[filename]['read']   
            new_files[new_filename]['filesize'] += old_files[filename]['filesize']  
        else:
            new_files[new_filename] = old_files[filename]
            
    
    return new_files

def combine_files(old_files, new_files):

    for filename in new_files:
        if filename in old_files:
            old_files[filename]['read'] += new_files[filename]['read']
        else:
            old_files[filename] = new_files[filename]


def pool_start(from_date, to_date):
    global working_files
    client = connect_elastic()
    if not gather_data(from_date, to_date, client):
            print("Failed to gather data")
            return False
    print(len(working_files))
    with open('{}.json'.format(from_date.strftime('%m-%Y-%d')), 'w') as tempdata:
        json.dump(working_files, tempdata)


def main():
    global working_files
    client = connect_elastic()
    # Gather data by month
    from_str = sys.argv[1]
    to_str = sys.argv[2]
    from_date = dateutil.parser.parse(from_str)
    #to_date = datetime.now()
    to_date = dateutil.parser.parse(to_str)
    cur_from_date = from_date
    interval = dateutil.relativedelta.relativedelta(months=1)
    cur_to_date = min(from_date + interval, to_date)
    print(f"Starting from {from_date} to {to_date} with interval {interval}")
    pool = Pool(processes=10)

    json_files = []
    
    while cur_from_date < to_date:
        print(cur_from_date)
        print(cur_to_date)
        json_filename = '{}.json'.format(cur_from_date.strftime('%m-%Y-%d'))
        json_files.append(json_filename)
        print(f"Checking for {json_filename}")
        if os.path.exists(json_filename):
            print(f"Found {json_filename}, moving on")
            cur_from_date += interval
            cur_to_date += interval
            cur_to_date = min(to_date, cur_to_date)
            continue

        print(f"Did not find data for {cur_from_date} to {cur_to_date}")
        pool.apply_async(pool_start, (cur_from_date, cur_to_date))

        #del working_files
        #working_files = {}
        cur_from_date += interval
        cur_to_date += interval
        cur_to_date = min(to_date, cur_to_date)
    
    # Now, wait for the pool to complete
    pool.close()
    print("Waiting for processing to complete")
    pool.join()
    
#    from_date = dateutil.parser.parse("2020-02-01")
#    to_date = datetime.now()
#    cur_from_date = from_date
#    cur_to_date = min(from_date + dateutil.relativedelta.relativedelta(days=1), to_date)
#    while cur_from_date < to_date:
#        print(cur_from_date)
#        print(cur_to_date)
#
#        if os.path.exists('{}.json'.format(cur_from_date.strftime('%d-%m-%Y'))):
#            cur_from_date += dateutil.relativedelta.relativedelta(days=1)
#            cur_to_date += dateutil.relativedelta.relativedelta(days=1)
#            cur_to_date = min(to_date, cur_to_date)
#            continue
#
#        if not gather_data(cur_from_date, cur_to_date, client):
#            continue
#        print(len(working_files))
#        with open('{}.json'.format(cur_from_date.strftime('%d-%m-%Y')), 'w') as tempdata:
#            json.dump(working_files, tempdata)
#
#        del working_files
#        working_files = {}
#        cur_from_date += dateutil.relativedelta.relativedelta(days=1)
#        cur_to_date += dateutil.relativedelta.relativedelta(days=1)
#        cur_to_date = min(to_date, cur_to_date)
#        
    # Post processing
    all_data = {}

    for filename in json_files:
        new_files = None
        with open(filename, 'r') as json_file:
            new_files = json.load(json_file)
        combine_files(all_data, new_files)
        del new_files
        print(len(all_data))

    combined_files = map_paths(all_data)
    print(combined_files)
    df = pd.DataFrame.from_dict(combined_files, orient='index')
    with open('output.csv', 'w') as output_file:
        df.to_csv(output_file)
        

if __name__ == "__main__":
    main()



