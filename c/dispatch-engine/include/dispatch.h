#ifndef DISPATCH_H
#define DISPATCH_H

typedef struct {
    int id;
    double lat;
    double lon;
} Location;

double haversine_distance(double lat1, double lon1, double lat2, double lon2);
int find_nearest_partner(Location order, Location* partners, int num_partners, double* out_distance);

#endif
