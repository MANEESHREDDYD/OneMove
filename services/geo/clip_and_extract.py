import json
import sys

import h3
import osmium


class BengaluruExtractor(osmium.SimpleHandler):
    def __init__(self):
        osmium.SimpleHandler.__init__(self)
        self.restaurants = []
        self.commercial = []
        self.roads = []
        # Bengaluru approximate BBOX
        self.min_lat, self.max_lat = 12.8340, 13.1436
        self.min_lon, self.max_lon = 77.4601, 77.7840
        self.nodes = {}

    def in_bbox(self, lat, lon):
        return (self.min_lat <= lat <= self.max_lat) and (self.min_lon <= lon <= self.max_lon)

    def node(self, n):
        if self.in_bbox(n.location.lat, n.location.lon):
            self.nodes[n.id] = (n.location.lat, n.location.lon)
            tags = {t.k: t.v for t in n.tags}
            if tags.get('amenity') == 'restaurant':
                h3_index = h3.geo_to_h3(n.location.lat, n.location.lon, 9)
                self.restaurants.append({
                    'id': n.id,
                    'lat': n.location.lat,
                    'lon': n.location.lon,
                    'h3_index': h3_index,
                    'name': tags.get('name', 'Unknown')
                })

    def way(self, w):
        tags = {t.k: t.v for t in w.tags}
        
        # Check if way is in bbox by checking its nodes
        # For simplicity in this streaming approach, if the first valid node is in bbox, we include it
        valid_nodes = [self.nodes[n.ref] for n in w.nodes if n.ref in self.nodes]
        if not valid_nodes:
            return

        # Extract Commercial Buildings
        if tags.get('building') == 'commercial':
            # Approximate center
            lat = sum(n[0] for n in valid_nodes) / len(valid_nodes)
            lon = sum(n[1] for n in valid_nodes) / len(valid_nodes)
            h3_index = h3.geo_to_h3(lat, lon, 9)
            self.commercial.append({
                'id': w.id,
                'lat': lat,
                'lon': lon,
                'h3_index': h3_index,
                'name': tags.get('name', 'Unknown')
            })

        # Extract Roads
        if 'highway' in tags:
            self.roads.append({
                'id': w.id,
                'type': tags['highway'],
                'name': tags.get('name', 'Unknown'),
                'nodes': valid_nodes
            })

def process_pbf(input_pbf, out_dir):
    extractor = BengaluruExtractor()
    extractor.apply_file(input_pbf, locations=True)
    
    with open(f"{out_dir}/bengaluru_restaurants.json", 'w') as f:
        json.dump(extractor.restaurants, f, indent=2)
        
    with open(f"{out_dir}/bengaluru_commercial.json", 'w') as f:
        json.dump(extractor.commercial, f, indent=2)
        
    with open(f"{out_dir}/bengaluru_roads.json", 'w') as f:
        json.dump(extractor.roads, f, indent=2)
        
    print(f"Extraction complete. Found {len(extractor.restaurants)} restaurants, {len(extractor.commercial)} commercial buildings, and {len(extractor.roads)} road segments.")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python clip_and_extract.py <input.pbf> <out_dir>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_directory = sys.argv[2]
    import os
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
        
    process_pbf(input_file, output_directory)
