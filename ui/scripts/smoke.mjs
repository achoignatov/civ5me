// Launch the built app hidden, let it detect + inspect the game (read-only), save a screenshot and status.
import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import electron from 'electron'

const out = await fs.mkdtemp(path.join(os.tmpdir(), 'civ5mm-smoke-'))
const p = spawn(electron, ['.'], { env: { ...process.env, CIV5MM_SMOKE_OUT: out }, stdio: 'inherit' })
p.on('exit', async (code) => {
  console.log(`exit ${code}; output in ${out}`)
  try {
    console.log(await fs.readFile(path.join(out, 'status.json'), 'utf8'))
  } catch {
    console.log('no status written')
  }
})
