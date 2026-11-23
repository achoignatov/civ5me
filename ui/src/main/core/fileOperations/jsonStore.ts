import fs from 'node:fs/promises'
import path from 'node:path'
import { isErrno } from './hash'

export async function readJson<T>(file: string): Promise<T | null> {
  let text: string
  try {
    text = await fs.readFile(file, 'utf8')
  } catch (e) {
    if (isErrno(e, 'ENOENT')) return null
    throw e
  }
  return JSON.parse(text) as T
}

/** Write JSON atomically (temp file + rename) so a crash never leaves a half-written state file. */
export async function writeJsonAtomic(file: string, data: unknown): Promise<void> {
  await fs.mkdir(path.dirname(file), { recursive: true })
  const tmp = `${file}.tmp-${process.pid}`
  const fh = await fs.open(tmp, 'w')
  try {
    await fh.writeFile(JSON.stringify(data, null, 2) + '\n', 'utf8')
    await fh.sync()
  } finally {
    await fh.close()
  }
  await fs.rename(tmp, file)
}
