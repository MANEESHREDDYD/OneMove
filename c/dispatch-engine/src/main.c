#include <stdio.h>
#include <stdlib.h>
#include "dispatch.h"

int main(int argc, char** argv) {
    if (argc < 3) {
        printf("Usage: ./dispatch_engine <orders_file> <partners_file>\n");
        return 1;
    }
    
    // In a full implementation, we would parse the CSV files here.
    // For this benchmark proof-of-concept, we will simulate loading 1000 orders and 1000 partners.
    Location orders[1000];
    Location partners[1000];
    
    for (int i = 0; i < 1000; i++) {
        orders[i] = (Location){i, 40.7128 + (rand() % 100) / 1000.0, -74.0060 + (rand() % 100) / 1000.0};
        partners[i] = (Location){i, 40.7128 + (rand() % 100) / 1000.0, -74.0060 + (rand() % 100) / 1000.0};
    }
    
    int matched = 0;
    for (int i = 0; i < 1000; i++) {
        double dist;
        int partner_id = find_nearest_partner(orders[i], partners, 1000, &dist);
        if (partner_id >= 0) matched++;
    }
    
    printf("Successfully dispatched %d orders.\n", matched);
    return 0;
}
