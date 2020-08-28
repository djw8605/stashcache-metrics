import pandas as pd

df = pd.read_csv('output2.csv')

# Convert the read and working set size to proper units

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

df['Data Read'] = df['read']
df['Working Set Size'] = df['filesize']


df['Data Read'] = df['Data Read'].apply(sizeof_fmt)
df['Working Set Size'] = df['Working Set Size'].apply(sizeof_fmt)
df['Reread Factor'] = df['read'] / df['filesize']
print(df.to_csv(index=False))


