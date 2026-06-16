package com.onemove.risk.controller;

import com.onemove.risk.model.OrderRiskRequest;
import com.onemove.risk.model.OrderRiskResponse;
import com.onemove.risk.service.OrderRiskService;
import com.onemove.risk.service.OrderLifecycleValidator;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/risk")
public class RiskController {

    private final OrderRiskService riskService;
    private final OrderLifecycleValidator lifecycleValidator;

    public RiskController(OrderRiskService riskService, OrderLifecycleValidator lifecycleValidator) {
        this.riskService = riskService;
        this.lifecycleValidator = lifecycleValidator;
    }

    @PostMapping("/score-order")
    public OrderRiskResponse scoreOrder(@RequestBody OrderRiskRequest request) {
        return riskService.evaluateOrderRisk(request);
    }

    @PostMapping("/validate-transition")
    public Map<String, Boolean> validateTransition(@RequestParam String current, @RequestParam String target) {
        return Map.of("isValid", lifecycleValidator.isValidTransition(current, target));
    }
    
    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "UP");
    }
}
