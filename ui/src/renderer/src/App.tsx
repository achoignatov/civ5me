import { useManager } from './hooks/useManager'
import { GamePath } from './components/GamePath'
import { ActiveConfig } from './components/ActiveConfig'
import { SwitchButtons } from './components/SwitchButtons'
import { StatusBar } from './components/StatusBar'

export default function App() {
  const { status, working, progress, message, gameRunning, refresh, switchTo } = useManager()
  const busy = working !== null || status?.busy === true
  return (
    <main>
      <header className="row">
        <h1 className="grow">Civilization V Mod Manager</h1>
        <button className="secondary" disabled={busy} onClick={() => void refresh()}>
          Re-check
        </button>
      </header>
      <GamePath game={status?.game ?? null} checking={working !== null && status === null} />
      <ActiveConfig active={status?.active ?? null} />
      <SwitchButtons status={status} disabled={busy || gameRunning} gameRunning={gameRunning} working={working} progress={progress} onSwitch={(id, name) => void switchTo(id, name)} />
      <StatusBar working={working} progress={progress} message={message} />
      {gameRunning && (
        <div className="game-running" role="alert">
          Civilization V is running. Close the game to switch between Vanilla BNW and Middle Earth.
        </div>
      )}
    </main>
  )
}
