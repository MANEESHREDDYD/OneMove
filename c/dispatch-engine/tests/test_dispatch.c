#include <stdio.h>
#include <assert.h>
#include "dispatch.h"

void test_haversine() {
    double dist = haversine_distance(40.7128, -74.0060, 40.7306, -73.9866);
    assert(dist > 2.0 && dist < 3.0); // Approx 2.5km
    printf("Haversine test passed.\n");
}

void test_nearest_partner() {
    Location order = {1, 40.7128, -74.0060};
    Location partners[2] = {
        {101, 40.7306, -73.9866}, // Far
        {102, 40.7130, -74.0065}  // Near
    };
    
    double dist;
    int best = find_nearest_partner(order, partners, 2, &dist);
    assert(best == 102);
    printf("Nearest partner test passed.\n");
}

int main() {
    test_haversine();
    test_nearest_partner();
    printf("All C unit tests passed.\n");
    return 0;
}
