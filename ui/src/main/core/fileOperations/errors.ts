/** An error whose message is meant to be shown to the user as is. */
export class UserError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'UserError'
  }
}

/** Turn a Node fs error into an understandable sentence. */
export function describeFsError(e: unknown, action: string, target: string): string {
  const err = e as NodeJS.ErrnoException
  switch (err?.code) {
    case 'EACCES':
    case 'EPERM':
      return (
        `Permission denied while trying to ${action} "${target}". Your user account can't write to this folder. ` +
        `Fix the folder permissions (on Linux: make sure the Steam library belongs to your user; on Windows: ` +
        `install Steam games outside protected folders or adjust the folder's security settings). ` +
        `This app never requests administrator/root rights by itself.`
      )
    case 'EBUSY':
      return `"${target}" is in use by another program (is Civilization V still running?). Could not ${action} it.`
    case 'ENOSPC':
      return `Not enough disk space to ${action} "${target}".`
    case 'EROFS':
      return `"${target}" is on a read-only filesystem; could not ${action} it.`
    case 'ENOENT':
      return `"${target}" does not exist; could not ${action} it.`
    default:
      return `Could not ${action} "${target}": ${err?.message ?? String(e)}`
  }
}

export function messageOf(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}
