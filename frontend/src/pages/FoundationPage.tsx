import { useEffect, useMemo, useState } from 'react'

import { AppShell } from '../layouts/AppShell'

const GRID_LIMIT = 60
const SOLAR_POWER = 12
const TARIFF = 0.92
const VEHICLES = ['GoodCar E1', 'Voltz City', 'E-Motion X', 'GoodCar E2']

function money(value: number) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
}

export function FoundationPage() {
  const [running, setRunning] = useState(false)
  const [minutes, setMinutes] = useState(0)
  const [completed, setCompleted] = useState(false)

  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => setMinutes((value) => Math.min(value + 1, 45)), 700)
    return () => window.clearInterval(timer)
  }, [running])

  useEffect(() => {
    if (minutes === 45) setRunning(false)
  }, [minutes])

  const allocated = running || minutes > 0 ? (GRID_LIMIT + SOLAR_POWER) / VEHICLES.length : 0
  const totalPower = allocated * VEHICLES.length
  const gridPower = Math.max(totalPower - SOLAR_POWER, 0)
  const energy = totalPower * minutes / 60
  const solarEnergy = Math.min(SOLAR_POWER, totalPower) * minutes / 60
  const cost = energy * TARIFF
  const progress = Math.round((minutes / 45) * 100)
  const invoiceVisible = completed || minutes === 45
  const chart = useMemo(() => [42, 48, 51, 58, gridPower || 60], [gridPower])

  function reset() {
    setRunning(false)
    setMinutes(0)
    setCompleted(false)
  }

  function finish() {
    setRunning(false)
    setCompleted(true)
  }

  return (
    <AppShell>
      <div className="demo-page">
        <header className="demo-header">
          <div>
            <p className="eyebrow">Central GoodWe · São Paulo</p>
            <h1>Operação inteligente de recarga</h1>
            <p>Simulação acelerada: 1 segundo representa 1 minuto de operação.</p>
          </div>
          <div className={`live-pill ${running ? 'live-pill--active' : ''}`}>
            <span /> {running ? 'Simulação em execução' : invoiceVisible ? 'Sessão finalizada' : 'Pronto para simular'}
          </div>
        </header>

        <section className="kpi-grid" aria-label="Indicadores da operação">
          <Kpi label="Demanda solicitada" value="80 kW" note="4 veículos × 20 kW" tone="warning" />
          <Kpi label="Potência distribuída" value={`${totalPower.toFixed(0)} kW`} note="Equal Share Allocation" tone="green" />
          <Kpi label="Limite da rede" value="60 kW" note={`${gridPower.toFixed(0)} kW em uso`} />
          <Kpi label="Energia solar" value={`${Math.min(SOLAR_POWER, totalPower).toFixed(0)} kW`} note="Prioridade renovável" tone="solar" />
        </section>

        <div className="dashboard-grid">
          <section className="panel demand-panel">
            <div className="panel__head">
              <div><p className="eyebrow">Entregável 01</p><h2>Gerenciamento de demanda</h2></div>
              <span className="safe-badge">✓ Rede protegida</span>
            </div>
            <div className="demand-summary">
              <div><span>Solicitado</span><strong>80 kW</strong></div><div className="flow-arrow">→</div>
              <div><span>Disponível</span><strong>72 kW</strong></div><div className="flow-arrow">→</div>
              <div><span>Rede</span><strong>{gridPower.toFixed(0)} / 60 kW</strong></div>
            </div>
            <div className="chart" aria-label="Histórico de demanda">
              {chart.map((value, index) => <div key={index} style={{ height: `${value / 0.8}%` }}><span>{value.toFixed(0)}</span></div>)}
              <i className="limit-line"><span>limite 60 kW</span></i>
            </div>
            <p className="insight">O sistema detectou excesso de 8 kW e redistribuiu automaticamente a potência entre as sessões.</p>
          </section>

          <section className="panel billing-panel">
            <div className="panel__head"><div><p className="eyebrow">Entregável 02</p><h2>Cobrança em tempo real</h2></div><span className="tariff">{money(TARIFF)}/kWh</span></div>
            <div className="bill-total"><span>Custo acumulado</span><strong>{money(cost)}</strong><small>{energy.toFixed(2)} kWh consumidos</small></div>
            <dl className="bill-breakdown">
              <div><dt>Energia solar</dt><dd>{solarEnergy.toFixed(2)} kWh</dd></div>
              <div><dt>Energia da rede</dt><dd>{Math.max(energy - solarEnergy, 0).toFixed(2)} kWh</dd></div>
              <div><dt>Modelo</dt><dd>Pay-per-use</dd></div>
            </dl>
            {invoiceVisible && <div className="invoice" role="status"><span>✓</span><div><strong>Invoice fechada</strong><small>Total calculado automaticamente: {money(cost)}</small></div></div>}
          </section>
        </div>

        <section className="panel sessions-panel">
          <div className="panel__head">
            <div><p className="eyebrow">Entregável 03</p><h2>Recargas inteligentes</h2></div>
            <div className="simulation-controls">
              <button className="button button--ghost" onClick={reset}>Reiniciar</button>
              {!running && !invoiceVisible && <button className="button" onClick={() => setRunning(true)}>▶ Iniciar simulação</button>}
              {running && <button className="button button--danger" onClick={finish}>■ Finalizar e cobrar</button>}
            </div>
          </div>
          <div className="session-table" role="table" aria-label="Sessões de recarga">
            <div className="session-row session-row--head" role="row"><span>Veículo</span><span>Carregador</span><span>Solicitado</span><span>Alocado</span><span>Progresso</span><span>Status</span></div>
            {VEHICLES.map((vehicle, index) => (
              <div className="session-row" role="row" key={vehicle}>
                <span><b className="vehicle-icon">⚡</b><strong>{vehicle}</strong></span><span>CG-{String(index + 1).padStart(2, '0')}</span><span>20 kW</span><span className="allocated">{allocated.toFixed(0)} kW</span>
                <span><i className="progress"><b style={{ width: `${progress}%` }} /></i><small>{progress}%</small></span>
                <span><em className={`status-chip ${invoiceVisible ? 'status-chip--done' : running ? '' : 'status-chip--idle'}`}>{invoiceVisible ? 'Concluída' : running ? 'Carregando' : 'Aguardando'}</em></span>
              </div>
            ))}
          </div>
          <footer className="session-footer"><span>Tempo simulado <strong>{String(minutes).padStart(2, '0')}:00 min</strong></span><span>Solar representa <strong>{energy ? ((solarEnergy / energy) * 100).toFixed(1) : '0.0'}%</strong> do consumo</span><span>CO₂ evitado <strong>{(solarEnergy * 0.084).toFixed(2)} kg</strong></span></footer>
        </section>
      </div>
    </AppShell>
  )
}

function Kpi({ label, value, note, tone = '' }: { label: string; value: string; note: string; tone?: string }) {
  return <article className={`kpi ${tone ? `kpi--${tone}` : ''}`}><span>{label}</span><strong>{value}</strong><small>{note}</small></article>
}
