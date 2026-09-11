# Introduction

The [RIPE Atlas] project allows users to create measurement studies
relating to pings, traceroutes and DNS requests from deployed
measurement nodes around the planet.  The results can then be viewed
within their measurement dashboard, or downloaded in JSON format to
study with your own tools.

`atlas2fsdb` specializes in converting DNS related research results
from RIPE Atlas into [FSDB] files, which become rapidly parsable in
perl's module or python's [pyfsdb] module, or viewable in
tools like [pyfsdb-viewer].

[RIPE Atlas]: https://atlas.ripe.net/
[FSDB]: https://ant.isi.edu/~johnh/SOFTWARE/FSDB/
[pyfsdb]: https://fsdb.readthedocs.io/en/latest/
[pyfsdb-viewer]: https://github.com/hardaker/pyfsdb-viewer

# Usage

1. Install it: `uv tool install atlas2fsdb`
2. Obtain a [RIPE Atlas] JSON file from a [broot-soa-test](DNS test result).
3. Convert it: `atlas2fsdb downloaded.json downloaded.fsdb`
4. Process it (e.g.): `pdbcoluniq -k rcode -c downloaded.fsdb`

[broot-soa-test**: https://atlas.ripe.net/measurements/3082611/results

**WARNING: currently, atlas downloads multi-json records per file (one
per line) and these must be converted to a JSON array...  this needs
to be accommodated in the future, but the quick hack is to add a `[`
at the top of the file, a ']' at the bottom and add a `,` to the end
of every line but the last.**

# Example processing commands

## Counting rcodes

``` bash
pdbcoluniq -k rcode -c downloaded.fsdb | pdbformat -f '{rcode:<20} {count}' 
```

``` text
NOERROR              517
```

## Getting the average response time

``` bash
dbstats response_time < downloaded.fsdb
```

``` text
#fsdb mean:d stddev:d pct_rsd:d conf_range:d conf_low:d conf_high:d conf_pct:d sum:d sum_squared:d min:d max:d n:q
39.432 41.953 106.39 3.6588 35.773 43.09 0.95 20386 1.712e+06 0.285 173.106 517
#  | ./atlas2fsdb/atlas2fsdb.py new.json new.fsdb
#   | dbcolstats response_time
```

## Getting average response time per ASN

(requires [ip2asn] installed)

[ip2asn]: https://github.com/hardaker/ip2asn

``` bash
cat new.fsdb | 
    ip2asn -I - -k probe_src | 
    dbcol ASN response_time | 
    dbmultistats -k ASN response_time | 
    dbcol ASN min mean max | 
    dbsort -n mean |
    pdbformat -f "{ASN:>7} {min:>10.03f} {max:>10.03f}"
```

``` text
 202422      0.359      1.419
   9268      0.710      1.148
  22548      1.255     11.331
    553      3.722     10.105
    559      5.529      7.128
   2486      7.174      7.814
   5539      7.183      8.503
  25192      7.563      7.607
```
