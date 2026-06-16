package com.onemove.risk.service;

import org.springframework.stereotype.Service;
import java.util.List;
import java.util.Arrays;

@Service
public class OrderLifecycleValidator {

    public boolean isValidTransition(String currentStatus, String targetStatus) {
        if ("pending".equals(currentStatus) && Arrays.asList("accepted", "cancelled").contains(targetStatus)) {
            return true;
        }
        if ("accepted".equals(currentStatus) && Arrays.asList("in_progress", "cancelled").contains(targetStatus)) {
            return true;
        }
        if ("in_progress".equals(currentStatus) && Arrays.asList("delivered", "cancelled").contains(targetStatus)) {
            return true;
        }
        return false;
    }
}
