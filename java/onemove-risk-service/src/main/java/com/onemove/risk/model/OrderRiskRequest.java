package com.onemove.risk.model;

public class OrderRiskRequest {
    private String orderId;
    private String customerId;
    private double fareAmount;
    private String zoneId;
    private String serviceType;
    private boolean isNewCustomer;

    // Getters and Setters
    public String getOrderId() { return orderId; }
    public void setOrderId(String orderId) { this.orderId = orderId; }
    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public double getFareAmount() { return fareAmount; }
    public void setFareAmount(double fareAmount) { this.fareAmount = fareAmount; }
    public String getZoneId() { return zoneId; }
    public void setZoneId(String zoneId) { this.zoneId = zoneId; }
    public String getServiceType() { return serviceType; }
    public void setServiceType(String serviceType) { this.serviceType = serviceType; }
    public boolean isNewCustomer() { return isNewCustomer; }
    public void setNewCustomer(boolean newCustomer) { isNewCustomer = newCustomer; }
}
