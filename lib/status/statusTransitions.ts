export const ORDER_STATUSES = [
  'requested', 'placed', 'created', 'merchant_accepted', 'preparing', 'ready', 
  'partner_assigned', 'assigned', 'accepted', 'arrived', 'started', 'picked_up', 
  'in_transit', 'delivered', 'completed', 'cancelled', 'refunded', 'pending'
] as const

export type OrderStatus = typeof ORDER_STATUSES[number]

export const VALID_TRANSITIONS: Record<string, Record<OrderStatus, OrderStatus[]>> = {
  ride: {
    requested: ['assigned', 'accepted', 'cancelled'],
    assigned: ['accepted', 'cancelled'],
    accepted: ['arrived', 'cancelled'],
    arrived: ['started', 'cancelled'],
    started: ['completed', 'cancelled'],
    completed: ['refunded'],
    cancelled: [],
    refunded: [],
    placed: [], created: [], merchant_accepted: [], preparing: [], ready: [], partner_assigned: [], picked_up: [], in_transit: [], delivered: [], pending: []
  },
  eats: {
    placed: ['merchant_accepted', 'cancelled'],
    merchant_accepted: ['preparing', 'cancelled'],
    preparing: ['ready', 'cancelled'],
    ready: ['partner_assigned', 'picked_up', 'cancelled'],
    partner_assigned: ['picked_up', 'cancelled'],
    picked_up: ['in_transit', 'cancelled'],
    in_transit: ['delivered', 'cancelled'],
    delivered: ['completed', 'refunded'],
    completed: ['refunded'],
    cancelled: [],
    refunded: [],
    requested: [], assigned: [], accepted: [], arrived: [], started: [], created: [], pending: []
  },
  grocery: {
    placed: ['merchant_accepted', 'cancelled'],
    merchant_accepted: ['preparing', 'cancelled'],
    preparing: ['ready', 'cancelled'],
    ready: ['partner_assigned', 'picked_up', 'cancelled'],
    partner_assigned: ['picked_up', 'cancelled'],
    picked_up: ['in_transit', 'cancelled'],
    in_transit: ['delivered', 'cancelled'],
    delivered: ['completed', 'refunded'],
    completed: ['refunded'],
    cancelled: [],
    refunded: [],
    requested: [], assigned: [], accepted: [], arrived: [], started: [], created: [], pending: []
  },
  courier: {
    created: ['partner_assigned', 'accepted', 'cancelled'],
    partner_assigned: ['accepted', 'cancelled'],
    accepted: ['picked_up', 'cancelled'],
    picked_up: ['in_transit', 'cancelled'],
    in_transit: ['delivered', 'cancelled'],
    delivered: ['completed', 'refunded'],
    completed: ['refunded'],
    cancelled: [],
    refunded: [],
    requested: [], assigned: [], arrived: [], started: [], placed: [], merchant_accepted: [], preparing: [], ready: [], pending: []
  }
}

export function isValidTransition(serviceType: string, currentStatus: OrderStatus, newStatus: OrderStatus): boolean {
  if (currentStatus === newStatus) return true
  
  const typeMap = VALID_TRANSITIONS[serviceType]
  if (!typeMap) return false

  const validNextStates = typeMap[currentStatus] || []
  return validNextStates.includes(newStatus)
}
