const { contextBridge, ipcRenderer, webUtils } = require('electron')

contextBridge.exposeInMainWorld('athenaDesktop', {
  getConnection: profile => ipcRenderer.invoke('athena:connection', profile),
  revalidateConnection: () => ipcRenderer.invoke('athena:connection:revalidate'),
  touchBackend: profile => ipcRenderer.invoke('athena:backend:touch', profile),
  getGatewayWsUrl: profile => ipcRenderer.invoke('athena:gateway:ws-url', profile),
  openSessionWindow: (sessionId, opts) => ipcRenderer.invoke('athena:window:openSession', sessionId, opts),
  openNewSessionWindow: () => ipcRenderer.invoke('athena:window:openNewSession'),
  getBootProgress: () => ipcRenderer.invoke('athena:boot-progress:get'),
  getConnectionConfig: profile => ipcRenderer.invoke('athena:connection-config:get', profile),
  saveConnectionConfig: payload => ipcRenderer.invoke('athena:connection-config:save', payload),
  applyConnectionConfig: payload => ipcRenderer.invoke('athena:connection-config:apply', payload),
  testConnectionConfig: payload => ipcRenderer.invoke('athena:connection-config:test', payload),
  probeConnectionConfig: remoteUrl => ipcRenderer.invoke('athena:connection-config:probe', remoteUrl),
  oauthLoginConnectionConfig: remoteUrl => ipcRenderer.invoke('athena:connection-config:oauth-login', remoteUrl),
  oauthLogoutConnectionConfig: remoteUrl => ipcRenderer.invoke('athena:connection-config:oauth-logout', remoteUrl),
  profile: {
    get: () => ipcRenderer.invoke('athena:profile:get'),
    set: name => ipcRenderer.invoke('athena:profile:set', name)
  },
  api: request => ipcRenderer.invoke('athena:api', request),
  notify: payload => ipcRenderer.invoke('athena:notify', payload),
  requestMicrophoneAccess: () => ipcRenderer.invoke('athena:requestMicrophoneAccess'),
  readFileDataUrl: filePath => ipcRenderer.invoke('athena:readFileDataUrl', filePath),
  readFileText: filePath => ipcRenderer.invoke('athena:readFileText', filePath),
  selectPaths: options => ipcRenderer.invoke('athena:selectPaths', options),
  writeClipboard: text => ipcRenderer.invoke('athena:writeClipboard', text),
  saveImageFromUrl: url => ipcRenderer.invoke('athena:saveImageFromUrl', url),
  saveImageBuffer: (data, ext) => ipcRenderer.invoke('athena:saveImageBuffer', { data, ext }),
  saveClipboardImage: () => ipcRenderer.invoke('athena:saveClipboardImage'),
  getPathForFile: file => {
    try {
      return webUtils.getPathForFile(file) || ''
    } catch {
      return ''
    }
  },
  normalizePreviewTarget: (target, baseDir) => ipcRenderer.invoke('athena:normalizePreviewTarget', target, baseDir),
  watchPreviewFile: url => ipcRenderer.invoke('athena:watchPreviewFile', url),
  stopPreviewFileWatch: id => ipcRenderer.invoke('athena:stopPreviewFileWatch', id),
  setTitleBarTheme: payload => ipcRenderer.send('athena:titlebar-theme', payload),
  setNativeTheme: mode => ipcRenderer.send('athena:native-theme', mode),
  setTranslucency: payload => ipcRenderer.send('athena:translucency', payload),
  setPreviewShortcutActive: active => ipcRenderer.send('athena:previewShortcutActive', Boolean(active)),
  openExternal: url => ipcRenderer.invoke('athena:openExternal', url),
  openPreviewInBrowser: url => ipcRenderer.invoke('athena:openPreviewInBrowser', url),
  fetchLinkTitle: url => ipcRenderer.invoke('athena:fetchLinkTitle', url),
  sanitizeWorkspaceCwd: cwd => ipcRenderer.invoke('athena:workspace:sanitize', cwd),
  settings: {
    getDefaultProjectDir: () => ipcRenderer.invoke('athena:setting:defaultProjectDir:get'),
    setDefaultProjectDir: dir => ipcRenderer.invoke('athena:setting:defaultProjectDir:set', dir),
    pickDefaultProjectDir: () => ipcRenderer.invoke('athena:setting:defaultProjectDir:pick')
  },
  revealLogs: () => ipcRenderer.invoke('athena:logs:reveal'),
  getRecentLogs: () => ipcRenderer.invoke('athena:logs:recent'),
  readDir: dirPath => ipcRenderer.invoke('athena:fs:readDir', dirPath),
  gitRoot: startPath => ipcRenderer.invoke('athena:fs:gitRoot', startPath),
  worktrees: cwds => ipcRenderer.invoke('athena:fs:worktrees', cwds),
  terminal: {
    dispose: id => ipcRenderer.invoke('athena:terminal:dispose', id),
    resize: (id, size) => ipcRenderer.invoke('athena:terminal:resize', id, size),
    start: options => ipcRenderer.invoke('athena:terminal:start', options),
    write: (id, data) => ipcRenderer.invoke('athena:terminal:write', id, data),
    onData: (id, callback) => {
      const channel = `athena:terminal:${id}:data`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)
      return () => ipcRenderer.removeListener(channel, listener)
    },
    onExit: (id, callback) => {
      const channel = `athena:terminal:${id}:exit`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)
      return () => ipcRenderer.removeListener(channel, listener)
    }
  },
  onClosePreviewRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('athena:close-preview-requested', listener)
    return () => ipcRenderer.removeListener('athena:close-preview-requested', listener)
  },
  onOpenUpdatesRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('athena:open-updates', listener)
    return () => ipcRenderer.removeListener('athena:open-updates', listener)
  },
  onDeepLink: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('athena:deep-link', listener)
    return () => ipcRenderer.removeListener('athena:deep-link', listener)
  },
  signalDeepLinkReady: () => ipcRenderer.invoke('athena:deep-link-ready'),
  onWindowStateChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('athena:window-state-changed', listener)
    return () => ipcRenderer.removeListener('athena:window-state-changed', listener)
  },
  onFocusSession: callback => {
    const listener = (_event, sessionId) => callback(sessionId)
    ipcRenderer.on('athena:focus-session', listener)
    return () => ipcRenderer.removeListener('athena:focus-session', listener)
  },
  onNotificationAction: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('athena:notification-action', listener)
    return () => ipcRenderer.removeListener('athena:notification-action', listener)
  },
  onPreviewFileChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('athena:preview-file-changed', listener)
    return () => ipcRenderer.removeListener('athena:preview-file-changed', listener)
  },
  onBackendExit: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('athena:backend-exit', listener)
    return () => ipcRenderer.removeListener('athena:backend-exit', listener)
  },
  onPowerResume: callback => {
    const listener = () => callback()
    ipcRenderer.on('athena:power-resume', listener)
    return () => ipcRenderer.removeListener('athena:power-resume', listener)
  },
  onBootProgress: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('athena:boot-progress', listener)
    return () => ipcRenderer.removeListener('athena:boot-progress', listener)
  },
  // First-launch bootstrap progress -- emitted by the install.ps1 stage
  // runner in main.cjs (apps/desktop/electron/bootstrap-runner.cjs).
  // Renderer's install overlay subscribes to live events and queries the
  // current snapshot via getBootstrapState() to recover after a devtools
  // reload mid-bootstrap.
  getBootstrapState: () => ipcRenderer.invoke('athena:bootstrap:get'),
  resetBootstrap: () => ipcRenderer.invoke('athena:bootstrap:reset'),
  repairBootstrap: () => ipcRenderer.invoke('athena:bootstrap:repair'),
  cancelBootstrap: () => ipcRenderer.invoke('athena:bootstrap:cancel'),
  onBootstrapEvent: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('athena:bootstrap:event', listener)
    return () => ipcRenderer.removeListener('athena:bootstrap:event', listener)
  },
  getVersion: () => ipcRenderer.invoke('athena:version'),
  getRemoteDisplayReason: () => ipcRenderer.invoke('athena:get-remote-display-reason'),
  uninstall: {
    summary: () => ipcRenderer.invoke('athena:uninstall:summary'),
    run: mode => ipcRenderer.invoke('athena:uninstall:run', { mode })
  },
  updates: {
    check: () => ipcRenderer.invoke('athena:updates:check'),
    apply: opts => ipcRenderer.invoke('athena:updates:apply', opts),
    getBranch: () => ipcRenderer.invoke('athena:updates:branch:get'),
    setBranch: name => ipcRenderer.invoke('athena:updates:branch:set', name),
    onProgress: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('athena:updates:progress', listener)
      return () => ipcRenderer.removeListener('athena:updates:progress', listener)
    }
  },
  themes: {
    fetchMarketplace: id => ipcRenderer.invoke('athena:vscode-theme:fetch', id),
    searchMarketplace: query => ipcRenderer.invoke('athena:vscode-theme:search', query)
  }
})
