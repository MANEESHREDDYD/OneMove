export const ORDER_STATUSES = [
  'requested', 'placed', 'created', 'merchant_accepted', 'preparing', 'ready', 
  'partner_assigned', 'arrived', 'started', 'picked_up', 'in_transit', 'delivered', 
  'completed', 'cancelled', 'refunded'
] as const

export type OrderStatus = typeof ORDER_STATUSES[number]

export const VALID_TRANSITIONS: Record<string, Record<OrderStatus, OrderStatus[]>> = {
  ride: {
    requested: ['partner_assigned', 'cancelled'],
    placed: [],
    created: [],
    merchant_accepted: [],
    preparing: [],
    ready: [],
    partner_assigned: ['arrived', 'cancelled'],
    arrived: ['started', 'cancelled'],
    started: ['completed', 'cancelled'],
    picked_up: [],
    in_transit: [],
    delivered: [],
    completed: ['refunded'],
    cancelled: [],
    refunded: []
  },
  eats: {
    requested: [],
    placed: ['merchant_accepted', 'cancelled'],
    created: [],
    merchant_accepted: ['preparing', 'cancelled'],
    preparing: ['ready', 'cancelled'],
    ready: ['partner_assigned', 'picked_up', 'cancelled'], // picked_up if self-pickup
    partner_assigned: ['picked_up', 'cancelled'],
    arrived: [],
    started: [],
    picked_up: ['in_transit', 'cancelled'],
    in_transit: ['delivered', 'cancelled'],
    delivered: ['completed', 'refunded'],
    completed: ['refunded'],
    cancelled: [],
    refunded: []
  },
  grocery: {
    requested: [],
    placed: ['merchant_accepted', 'cancelled'],
    created: [],
    merchant_accepted: ['preparing', 'cancelled'],
    preparing: ['ready', 'cancelled'],
    ready: ['partner_assigned', 'picked_up', 'cancelled'],
    partner_assigned: ['picked_up', 'cancelled'],
    arrived: [],
    started: [],
    picked_up: ['in_transit', 'cancelled'],
    in_transit: ['delivered', 'cancelled'],
    delivered: ['completed', 'refunded'],
    completed: ['refunded'],
    cancelled: [],
    refunded: []
  },
  courier: {
    requested: [],
    placed: [],
    created: ['partner_assigned', 'cancelled'],
    merchant_accepted: [],
    preparing: [],
    ready: [],
    partner_assigned: ['arrived', 'cancelled'],
    arrived: ['picked_up', 'cancelled'],
    started: [],
    picked_up: ['in_transit', 'cancelled'],
    in_transit: ['delivered', 'cancelled'],
    delivered: ['completed', 'refunded'],
    completed: ['refunded'],
    cancelled: [],
    refunded: []
  }
}

export function isValidTransition(serviceType: string, currentStatus: OrderStatus, newStatus: OrderStatus): boolean {
  if (currentStatus === newStatus) return true
  
  const typeMap = VALID_TRANSITIONS[serviceType]
  if (!typeMap) return false // Unknown service type

  const validNextStates = typeMap[currentStatus] || []
  
  // Note: Admin bypass might ignore this function
  return validNextStates.includes(newStatus)
}
