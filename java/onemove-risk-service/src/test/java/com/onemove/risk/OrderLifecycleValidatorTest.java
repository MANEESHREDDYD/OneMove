package com.onemove.risk;

import com.onemove.risk.service.OrderLifecycleValidator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class OrderLifecycleValidatorTest {

    private final OrderLifecycleValidator validator = new OrderLifecycleValidator();

    @Test
    void testValidTransitions() {
        assertTrue(validator.isValidTransition("pending", "accepted"));
        assertTrue(validator.isValidTransition("accepted", "in_progress"));
    }

    @Test
    void testInvalidTransitions() {
        assertFalse(validator.isValidTransition("pending", "delivered"));
        assertFalse(validator.isValidTransition("delivered", "in_progress"));
    }
}
