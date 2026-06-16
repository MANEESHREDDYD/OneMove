package com.onemove.risk.model;

import java.util.List;

public class OrderRiskResponse {
    private boolean isApproved;
    private double riskScore;
    private List<String> flags;

    public OrderRiskResponse() {}

    public OrderRiskResponse(boolean isApproved, double riskScore, List<String> flags) {
        this.isApproved = isApproved;
        this.riskScore = riskScore;
        this.flags = flags;
    }

    public boolean isApproved() { return isApproved; }
    public void setApproved(boolean approved) { isApproved = approved; }
    public double getRiskScore() { return riskScore; }
    public void setRiskScore(double riskScore) { this.riskScore = riskScore; }
    public List<String> getFlags() { return flags; }
    public void setFlags(List<String> flags) { this.flags = flags; }
}
