#include "dispatch.h"

int find_nearest_partner(Location order, Location* partners, int num_partners, double* out_distance) {
    int best_id = -1;
    double min_dist = 9999999.0;
    
    for (int i = 0; i < num_partners; i++) {
        double dist = haversine_distance(order.lat, order.lon, partners[i].lat, partners[i].lon);
        if (dist < min_dist) {
            min_dist = dist;
            best_id = partners[i].id;
        }
    }
    
    *out_distance = min_dist;
    return best_id;
}
