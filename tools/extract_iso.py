import pycdlib, os, sys
iso = pycdlib.PyCdlib(); iso.open(sys.argv[1])
out = sys.argv[2]
for root, dirs, files in iso.walk(iso_path='/'):
    for f in files:
        p = root.rstrip('/') + '/' + f
        rec = iso.get_record(iso_path=p)
        name = p.split(';')[0]
        dst = os.path.join(out, name.lstrip('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        iso.get_file_from_iso(dst, iso_path=p)
        print(f"{rec.extent_location():8d} {rec.data_length:10d} {name}")
