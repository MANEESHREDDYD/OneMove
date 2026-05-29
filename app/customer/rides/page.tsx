import { PageHeader } from "@/components/common/PageHeader"
import { RideBookingForm } from "./RideBookingForm"

export default function CustomerRides() {
  return (
    <div className="space-y-6">
      <PageHeader 
        title="Request a Ride" 
        description="Where are you heading today?"
      />
      <RideBookingForm />
    </div>
  )
}
