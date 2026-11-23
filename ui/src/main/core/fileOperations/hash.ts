import { createHash } from 'node:crypto'
import { createReadStream } from 'node:fs'

export function sha256File(file: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const h = createHash('sha256')
    const s = createReadStream(file)
    s.on('error', reject)
    s.on('data', (d) => h.update(d))
    s.on('end', () => resolve(h.digest('hex')))
  })
}

/** sha256 of the file, or null if it does not exist. Other errors (permissions, ...) are thrown. */
export async function sha256OrNull(file: string): Promise<string | null> {
  try {
    return await sha256File(file)
  } catch (e) {
    if (isErrno(e, 'ENOENT') || isErrno(e, 'ENOTDIR')) return null
    throw e
  }
}

export function isErrno(e: unknown, code: string): boolean {
  return typeof e === 'object' && e !== null && (e as NodeJS.ErrnoException).code === code
}
