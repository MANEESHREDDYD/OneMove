export const METRICS = {
  GMV: {
    id: 'gmv',
    name: 'Gross Merchandise Value',
    description: 'Total dollar value of all non-cancelled orders.',
    unit: 'currency'
  },
  NET_REVENUE: {
    id: 'net_revenue',
    name: 'Net Revenue',
    description: 'Estimated net platform revenue (e.g., 20% take rate).',
    unit: 'currency'
  },
  TOTAL_ORDERS: {
    id: 'total_orders',
    name: 'Total Orders',
    description: 'Count of all orders placed.',
    unit: 'number'
  },
  COMPLETED_ORDERS: {
    id: 'completed_orders',
    name: 'Completed Orders',
    description: 'Count of successfully fulfilled orders.',
    unit: 'number'
  },
  CANCELLED_ORDERS: {
    id: 'cancelled_orders',
    name: 'Cancelled Orders',
    description: 'Count of cancelled orders.',
    unit: 'number'
  },
  REFUND_RATE: {
    id: 'refund_rate',
    name: 'Refund Rate',
    description: 'Percentage of completed orders that had a refund.',
    unit: 'percentage'
  },
  ACTIVE_CUSTOMERS: {
    id: 'active_customers',
    name: 'Active Customers',
    description: 'Unique customers who placed an order.',
    unit: 'number'
  },
  ACTIVE_PARTNERS: {
    id: 'active_partners',
    name: 'Active Partners',
    description: 'Unique partners who completed a job.',
    unit: 'number'
  },
  ACTIVE_MERCHANTS: {
    id: 'active_merchants',
    name: 'Active Merchants',
    description: 'Unique merchants who fulfilled an order.',
    unit: 'number'
  }
};
