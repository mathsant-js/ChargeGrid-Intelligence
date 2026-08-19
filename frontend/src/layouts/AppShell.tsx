import type { PropsWithChildren } from 'react'

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="ChargeGrid Intelligence">
          <span className="brand__mark">CG</span>
          <span>ChargeGrid Intelligence</span>
        </a>
        <span className="phase">Fase 1 · Fundação</span>
      </header>
      <main>{children}</main>
    </div>
  )
}
