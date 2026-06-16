package com.onemove.risk;

import com.onemove.risk.model.OrderRiskRequest;
import com.onemove.risk.model.OrderRiskResponse;
import com.onemove.risk.service.OrderRiskService;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class OrderRiskServiceTest {

    private final OrderRiskService service = new OrderRiskService();

    @Test
    void testLowRiskOrder() {
        OrderRiskRequest req = new OrderRiskRequest();
        req.setFareAmount(25.0);
        req.setNewCustomer(false);
        req.setZoneId("manhattan");

        OrderRiskResponse res = service.evaluateOrderRisk(req);
        assertTrue(res.isApproved());
        assertEquals(0.0, res.getRiskScore());
        assertTrue(res.getFlags().isEmpty());
    }

    @Test
    void testHighFareRisk() {
        OrderRiskRequest req = new OrderRiskRequest();
        req.setFareAmount(600.0);
        req.setNewCustomer(true);
        req.setZoneId("manhattan");

        OrderRiskResponse res = service.evaluateOrderRisk(req);
        assertFalse(res.isApproved());
        assertTrue(res.getFlags().contains("HIGH_FARE_AMOUNT"));
        assertTrue(res.getFlags().contains("NEW_CUSTOMER_HIGH_FARE"));
    }
}
