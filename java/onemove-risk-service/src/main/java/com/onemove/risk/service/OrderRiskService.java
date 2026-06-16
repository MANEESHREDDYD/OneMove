package com.onemove.risk.service;

import com.onemove.risk.model.OrderRiskRequest;
import com.onemove.risk.model.OrderRiskResponse;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class OrderRiskService {
    
    public OrderRiskResponse evaluateOrderRisk(OrderRiskRequest request) {
        double riskScore = 0.0;
        List<String> flags = new ArrayList<>();

        if (request.getFareAmount() > 500.0) {
            riskScore += 0.5;
            flags.add("HIGH_FARE_AMOUNT");
        }
        
        if (request.isNewCustomer() && request.getFareAmount() > 150.0) {
            riskScore += 0.4;
            flags.add("NEW_CUSTOMER_HIGH_FARE");
        }

        if ("high_risk_zone_mock".equals(request.getZoneId())) {
            riskScore += 0.3;
            flags.add("UNUSUAL_ZONE_ACTIVITY");
        }

        boolean approved = riskScore < 0.8;
        return new OrderRiskResponse(approved, Math.min(riskScore, 1.0), flags);
    }
}
