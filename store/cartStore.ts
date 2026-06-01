import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface CartItem {
  id: string; // Product ID
  merchant_id: string;
  name: string;
  price: number;
  quantity: number;
  image_url?: string;
  service_type: 'eats' | 'grocery';
}

interface CartState {
  items: CartItem[];
  addItem: (item: Omit<CartItem, 'quantity'>) => void;
  removeItem: (id: string) => void;
  updateQuantity: (id: string, delta: number) => void;
  clearCart: () => void;
  getMerchantId: () => string | null;
  getServiceType: () => 'eats' | 'grocery' | null;
  getSubtotal: () => number;
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],
      addItem: (newItem) => set((state) => {
        // Enforce single merchant per cart
        if (state.items.length > 0 && state.items[0].merchant_id !== newItem.merchant_id) {
          // If different merchant, clear cart first
          return { items: [{ ...newItem, quantity: 1 }] };
        }
        
        const existing = state.items.find(i => i.id === newItem.id);
        if (existing) {
          return {
            items: state.items.map(i => 
              i.id === newItem.id ? { ...i, quantity: i.quantity + 1 } : i
            )
          };
        }
        return { items: [...state.items, { ...newItem, quantity: 1 }] };
      }),
      removeItem: (id) => set((state) => ({
        items: state.items.filter(i => i.id !== id)
      })),
      updateQuantity: (id, delta) => set((state) => ({
        items: state.items.map(i => {
          if (i.id === id) {
            const newQ = Math.max(0, i.quantity + delta);
            return { ...i, quantity: newQ };
          }
          return i;
        }).filter(i => i.quantity > 0)
      })),
      clearCart: () => set({ items: [] }),
      getMerchantId: () => {
        const items = get().items;
        return items.length > 0 ? items[0].merchant_id : null;
      },
      getServiceType: () => {
        const items = get().items;
        return items.length > 0 ? items[0].service_type : null;
      },
      getSubtotal: () => get().items.reduce((sum, item) => sum + (item.price * item.quantity), 0)
    }),
    {
      name: 'onemove-cart',
    }
  )
);
