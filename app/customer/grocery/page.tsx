import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import Link from "next/link"
import { ShoppingBasket, Clock, CheckCircle2 } from "lucide-react"

const MOCK_GROCERY_STORES = [
  {
    id: "groc-200",
    name: "Fresh Market Plus",
    category: "Organic Produce",
    rating: 4.8,
    deliveryTime: "30-45 min",
    deliveryFee: 4.99,
    featured: true,
  },
  {
    id: "groc-201",
    name: "City Supermarket",
    category: "Everyday Essentials",
    rating: 4.6,
    deliveryTime: "40-60 min",
    deliveryFee: 5.99,
    featured: false,
  },
  {
    id: "groc-202",
    name: "Corner Deli & Mart",
    category: "Quick Snacks & Drinks",
    rating: 4.9,
    deliveryTime: "15-25 min",
    deliveryFee: 1.99,
    featured: true,
  }
]

export default function GroceryMarketplace() {
  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="OneMove Grocery" 
        description="Fresh groceries delivered to your door."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {MOCK_GROCERY_STORES.map(store => (
          <Link key={store.id} href={`/customer/grocery/${store.id}`} className="block group">
            <GlassCard className="p-0 overflow-hidden hover:ring-2 hover:ring-primary/50 transition-all cursor-pointer h-full flex flex-col border border-primary/20">
              <div className="h-32 bg-primary/10 w-full flex items-center justify-center relative overflow-hidden group-hover:bg-primary/20 transition-colors">
                 <div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent" />
                 <ShoppingBasket className="h-10 w-10 text-primary opacity-20 relative z-10" />
                 <p className="absolute bottom-3 left-4 text-sm font-bold">{store.category}</p>
                 {store.featured && (
                   <div className="absolute top-3 right-3 bg-green-500/20 text-green-500 px-2 py-1 rounded text-xs font-bold flex items-center gap-1 border border-green-500/20">
                     <CheckCircle2 className="h-3 w-3" /> Partner
                   </div>
                 )}
              </div>
              <div className="p-4 flex flex-col flex-1 justify-between">
                <div>
                  <h3 className="font-bold text-lg leading-tight mb-1">{store.name}</h3>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground font-medium mb-4">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {store.deliveryTime}
                    </span>
                    <span>•</span>
                    <span>${store.deliveryFee} fee</span>
                  </div>
                </div>
                <div className="text-sm text-primary font-semibold flex items-center justify-between">
                  Shop Now →
                  <span className="text-xs text-muted-foreground bg-primary/10 px-2 py-1 rounded-full border border-primary/20">
                    ★ {store.rating}
                  </span>
                </div>
              </div>
            </GlassCard>
          </Link>
        ))}
      </div>
    </div>
  )
}
