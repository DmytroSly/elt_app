from dlt.sources.filesystem import filesystem, read_csv

filesystem_source = filesystem() | read_csv()

data = list(filesystem_source)
for record in data:
    print(record)