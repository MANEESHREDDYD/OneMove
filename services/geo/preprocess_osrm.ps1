$ErrorActionPreference = "Stop"

$pbfFile = ".\data\osm\southern-zone-latest.osm.pbf"
$bengaluruPbf = ".\data\osm\bengaluru.osm.pbf"

Write-Host "Clipping Bengaluru bounding box using osmium-tool..."
# Bounding box for Bengaluru
docker run --rm -v ${PWD}\data\osm:/data stefanb/osmium-tool osmium extract -b 77.4601,12.8340,77.7840,13.1436 /data/southern-zone-latest.osm.pbf -o /data/bengaluru.osm.pbf --overwrite

Write-Host "Preprocessing routing graph with OSRM (Car profile)..."
docker run --rm -v ${PWD}\data\osm:/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/bengaluru.osm.pbf
docker run --rm -v ${PWD}\data\osm:/data osrm/osrm-backend osrm-partition /data/bengaluru.osm.pbf
docker run --rm -v ${PWD}\data\osm:/data osrm/osrm-backend osrm-customize /data/bengaluru.osm.pbf

Write-Host "OSRM preprocessing complete. To run the server:"
Write-Host "docker run -t -i -p 5000:5000 -v ${PWD}\data\osm:/data osrm/osrm-backend osrm-routed --algorithm mld /data/bengaluru.osm.pbf"

Write-Host "Generating sample route request..."
Write-Host "curl http://localhost:5000/route/v1/driving/77.5946,12.9716;77.6206,12.9352?overview=false"
