import type { ReactNode } from 'react'

export function DashboardCard({ label, value, detail }: { label: string; value: ReactNode; detail?: string }) {
  return <article className="dashboard-card"><h3>{label}</h3><strong>{value}</strong>{detail && <p>{detail}</p>}</article>
}
