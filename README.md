Retrieve stuff from CVP

see https://github.com/aristanetworks/cloudvision-python for original code

# Reading BGP routes
```
python3.9 -m venv myenv
source myenv/bin/activate
pip install --upgrade pip setuptools
pip install https://codeload.github.com/aristanetworks/cloudvision-python/tar.gz/refs/tags/v1.1.0
pip install requests

python get_token.py  --server cvp.net --username leuser --password "${PPASS}" --ssl
python get_routes.py --auth token,token.txt,cvp.crt  --apiserver cvp.net:8443 --vrf levrf | tee fip.csv

for i in `cut -d , -f 2 fip.csv  | sort -u` ; do C=$(grep ,${i}, fip.csv | cut -d , -f 2- | sort -u | wc -l) ; [[ $C != 1 ]] && echo failing $i; done
for i in `cut -d , -f 2 fip.csv | grep 10.91.13 | sort -u ` ; do grep $i realfiplist >/dev/null || echo $i should not be there ; done
```

# Expose BGP status through prometheus

```
python cvpexporter.py -t cvptoken -d -s

curl localhost:8000 | grep bgp

```
