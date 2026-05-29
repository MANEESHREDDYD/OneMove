export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string
          role: 'customer' | 'driver' | 'merchant' | 'admin'
          full_name: string
          phone: string | null
          avatar_url: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id: string
          role?: 'customer' | 'driver' | 'merchant' | 'admin'
          full_name: string
          phone?: string | null
          avatar_url?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          role?: 'customer' | 'driver' | 'merchant' | 'admin'
          full_name?: string
          phone?: string | null
          avatar_url?: string | null
          updated_at?: string
        }
      }
      merchants: {
        Row: {
          id: string
          owner_id: string
          name: string
          description: string | null
          category: 'restaurant' | 'grocery' | 'retail'
          status: string
          rating: number
          address_line1: string
          latitude: number
          longitude: number
          created_at: string
          updated_at: string
        }
      }
      products: {
        Row: {
          id: string
          merchant_id: string
          name: string
          description: string | null
          price: number
          image_url: string | null
          is_available: boolean
          category: string | null
          created_at: string
          updated_at: string
        }
      }
      vehicles: {
        Row: {
          id: string
          driver_id: string
          make: string
          model: string
          plate_number: string
          color: string
          type: 'car' | 'bike' | 'scooter'
          created_at: string
          updated_at: string
        }
      }
      orders: {
        Row: {
          id: string
          customer_id: string
          merchant_id: string | null
          driver_id: string | null
          service_type: 'ride' | 'eats' | 'grocery' | 'courier'
          status: 'pending' | 'accepted' | 'preparing' | 'ready' | 'in_transit' | 'completed' | 'cancelled'
          total_amount: number
          pickup_location: Json
          dropoff_location: Json
          scheduled_at: string | null
          created_at: string
          updated_at: string
        }
      }
      order_items: {
        Row: {
          id: string
          order_id: string
          product_id: string
          quantity: number
          price_at_time: number
          created_at: string
        }
      }
      payments: {
        Row: {
          id: string
          order_id: string
          customer_id: string
          amount: number
          status: 'pending' | 'processing' | 'succeeded' | 'failed' | 'refunded'
          stripe_payment_intent_id: string | null
          created_at: string
          updated_at: string
        }
      }
      tracking: {
        Row: {
          driver_id: string
          is_online: boolean
          current_location: Json | null
          last_updated: string
        }
      }
    }
  }
}
