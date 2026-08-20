import { useCallback, useEffect, useState } from 'react'
import './index.css'
import { api } from './api'
import StatusPanel from './components/StatusPanel'
import ActionsPanel from './components/ActionsPanel'
import ApprovalPanel from './components/ApprovalPanel'
import DecisionsTable from './components/DecisionsTable'
import BacktestTable from './components/BacktestTable'

const STATUS_POLL_MS = 5000

export default function App() {
  const [status, setStatus] = useState(null)
  const [statusError, setStatusError] = useState(null)
  const [decisions, setDecisions] = useState([])
  const [report, setReport] = useState(null)

  const refreshStatus = useCallback(() => {
    api
      .status()
      .then((data) => {
        setStatus(data)
        setStatusError(null)
      })
      .catch((err) => setStatusError(err.message))
  }, [])

  const refreshDecisions = useCallback(() => {
    api
      .decisions(30)
      .then((data) => setDecisions(data.decisions))
      .catch(() => {})
  }, [])

  const refreshReport = useCallback(() => {
    api
      .backtestReport()
      .then((data) => setReport(data.report))
      .catch(() => {})
  }, [])

  useEffect(() => {
    refreshStatus()
    refreshDecisions()
    refreshReport()
    const interval = setInterval(refreshStatus, STATUS_POLL_MS)
    return () => clearInterval(interval)
  }, [refreshStatus, refreshDecisions, refreshReport])

  return (
    <div className="app">
      <header>
        <h1>zoeTrading &mdash; suivi local</h1>
        <p className="banner">
          Interface locale (127.0.0.1). Aucun resultat affiche ici n&apos;est une garantie de gain, et AUTO reste
          inaccessible depuis cette interface. L&apos;approbation MANUAL peut se faire ici ou dans MT5 &mdash; les
          deux ecrivent dans le meme fichier de commande, aucune priorite entre les deux.
        </p>
      </header>

      <main>
        <StatusPanel status={status} error={statusError} />
        <ActionsPanel
          onScanned={() => {
            refreshStatus()
            refreshDecisions()
          }}
          onBacktested={(result) => {
            setReport(result)
          }}
        />
        <ApprovalPanel />
        <DecisionsTable decisions={decisions} />
        <BacktestTable report={report} />
      </main>
    </div>
  )
}
