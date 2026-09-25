import type { PropsWithChildren } from 'react'
import { Link, useLocation } from 'react-router-dom'

export function AppShell({ children }: PropsWithChildren) {
  const location = useLocation()
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" to="/" aria-label="ChargeGrid Intelligence">
          <span className="brand__mark">CG</span>
          <span>ChargeGrid Intelligence</span>
        </Link>
        {location.pathname.startsWith('/admin') && <nav aria-label="Navegação principal"><Link to="/admin">Dashboard</Link><Link to="/admin/operacao">Operação</Link></nav>}
      </header>
      <main>{children}</main>
    </div>
  )
}
