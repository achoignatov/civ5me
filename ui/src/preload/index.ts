import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron'
import type { ManagerApi, Progress } from '../shared/types'

// The only API the renderer gets: five calls and a progress subscription. No fs, no paths in, no ipcRenderer.
const api: ManagerApi = {
  getStatus: () => ipcRenderer.invoke('status:get'),
  refresh: () => ipcRenderer.invoke('status:refresh'),
  switchTo: (id: string) => ipcRenderer.invoke('config:switch', id),
  isGameRunning: () => ipcRenderer.invoke('game:running'),
  onProgress: (listener) => {
    const h = (_e: IpcRendererEvent, p: Progress) => listener(p)
    ipcRenderer.on('progress', h)
    return () => ipcRenderer.removeListener('progress', h)
  }
}

contextBridge.exposeInMainWorld('civ5mm', api)
