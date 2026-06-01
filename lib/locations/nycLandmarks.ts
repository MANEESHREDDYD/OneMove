export type Landmark = {
  name: string
  address: string
  lat: number
  lng: number
  zone: string
}

export const nycLandmarks: Landmark[] = [
  { name: 'JFK Airport', address: 'Queens, NY 11430', lat: 40.6413, lng: -73.7781, zone: 'Queens' },
  { name: 'Times Square', address: 'Manhattan, NY 10036', lat: 40.7580, lng: -73.9855, zone: 'Manhattan' },
  { name: 'Penn Station', address: 'New York, NY 10001', lat: 40.7506, lng: -73.9935, zone: 'Manhattan' },
  { name: 'Grand Central Terminal', address: '89 E 42nd St, New York, NY 10017', lat: 40.7527, lng: -73.9772, zone: 'Manhattan' },
  { name: 'Central Park', address: 'New York, NY', lat: 40.7812, lng: -73.9665, zone: 'Manhattan' },
  { name: 'Wall Street', address: 'New York, NY 10005', lat: 40.7074, lng: -74.0113, zone: 'Manhattan' },
  { name: 'Brooklyn Bridge', address: 'New York, NY 10038', lat: 40.7061, lng: -73.9969, zone: 'Brooklyn/Manhattan' },
  { name: 'LaGuardia Airport', address: 'Queens, NY 11371', lat: 40.7769, lng: -73.8740, zone: 'Queens' },
  { name: 'SoHo', address: 'New York, NY', lat: 40.7233, lng: -74.0030, zone: 'Manhattan' },
  { name: 'Williamsburg', address: 'Brooklyn, NY', lat: 40.7081, lng: -73.9571, zone: 'Brooklyn' },
  { name: 'DUMBO', address: 'Brooklyn, NY', lat: 40.7033, lng: -73.9881, zone: 'Brooklyn' },
  { name: 'Union Square', address: 'New York, NY', lat: 40.7359, lng: -73.9911, zone: 'Manhattan' },
  { name: 'Chelsea Market', address: '75 9th Ave, New York, NY 10011', lat: 40.7420, lng: -74.0048, zone: 'Manhattan' },
  { name: 'NYU', address: 'New York, NY 10012', lat: 40.7295, lng: -73.9965, zone: 'Manhattan' },
  { name: 'Columbia University', address: '116th St & Broadway, New York, NY 10027', lat: 40.8075, lng: -73.9626, zone: 'Manhattan' }
]
