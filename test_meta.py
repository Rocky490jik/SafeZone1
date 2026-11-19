import urllib.request, re

html = urllib.request.urlopen('http://127.0.0.1:5000/', timeout=10).read().decode()
m = re.search(r'<meta name="map-attribution"[^>]+>', html)
if m:
    print("map-attribution meta tag:")
    print(m.group(0)[:500])
else:
    print("map-attribution meta tag NOT FOUND")

m2 = re.search(r'<meta name="map-tile-url"[^>]+>', html)
if m2:
    print("\nmap-tile-url meta tag:")
    print(m2.group(0)[:500])
else:
    print("map-tile-url meta tag NOT FOUND")

m3 = re.search(r'<meta name="default-lat"[^>]+>', html)
if m3:
    print("\ndefault-lat meta tag:")
    print(m3.group(0)[:200])
else:
    print("default-lat meta tag NOT FOUND")