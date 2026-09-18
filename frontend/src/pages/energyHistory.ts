import type { EnergyReading } from '../api/client'

export function aggregateEnergyHistory(readings: EnergyReading[]) {
  const byTimestamp = new Map<string, { timestamp: string; demand: number; solar: number; grid: number }>()
  for (const reading of readings) {
    const point = byTimestamp.get(reading.timestamp) ?? {
      timestamp: reading.timestamp, demand: 0, solar: 0, grid: 0,
    }
    point.demand += reading.allocated_power_kw
    point.solar += reading.solar_power_kw
    point.grid += reading.grid_power_kw
    byTimestamp.set(reading.timestamp, point)
  }
  return [...byTimestamp.values()].sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp))
}
