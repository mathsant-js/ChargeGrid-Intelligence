import { describe, expect, it } from 'vitest'
import { aggregateEnergyHistory } from './energyHistory'
import type { EnergyReading } from '../api/client'

describe('aggregateEnergyHistory', () => {
  it('sums concurrent sessions into one station demand point per tick', () => {
    const readings = [
      { id: 'a', timestamp: '2026-09-16T12:01:00Z', allocated_power_kw: 20, solar_power_kw: 5, grid_power_kw: 15 },
      { id: 'b', timestamp: '2026-09-16T12:00:00Z', allocated_power_kw: 20, solar_power_kw: 0, grid_power_kw: 20 },
      { id: 'c', timestamp: '2026-09-16T12:01:00Z', allocated_power_kw: 20, solar_power_kw: 5, grid_power_kw: 15 },
    ] as EnergyReading[]
    expect(aggregateEnergyHistory(readings)).toEqual([
      { timestamp: '2026-09-16T12:00:00Z', demand: 20, solar: 0, grid: 20 },
      { timestamp: '2026-09-16T12:01:00Z', demand: 40, solar: 10, grid: 30 },
    ])
  })
})
