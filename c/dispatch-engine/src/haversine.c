#include <math.h>
#include "dispatch.h"

#define EARTH_RADIUS_KM 6371.0

double to_radians(double degrees) {
    return degrees * M_PI / 180.0;
}

double haversine_distance(double lat1, double lon1, double lat2, double lon2) {
    double dlat = to_radians(lat2 - lat1);
    double dlon = to_radians(lon2 - lon1);
    
    double a = sin(dlat / 2.0) * sin(dlat / 2.0) +
               cos(to_radians(lat1)) * cos(to_radians(lat2)) *
               sin(dlon / 2.0) * sin(dlon / 2.0);
               
    double c = 2.0 * atan2(sqrt(a), sqrt(1.0 - a));
    return EARTH_RADIUS_KM * c;
}
