import { contextBridge, ipcRenderer, webFrame, webUtils } from 'electron'

// Which translucency the OS can back. Asked synchronously because the renderer
// needs it before its first paint, and answered by main because deciding it
// needs `os.release()` — a sandboxed preload may only require electron, events,
// timers and url, so importing node:os here throws before contextBridge runs
// and takes the ENTIRE bridge down with it (window.athenaDesktop undefined =>
// "Desktop IPC bridge is unavailable"). No reply means no glass, which degrades
// to an ordinary opaque window rather than a page thinned over nothing.
const translucencySupport = ipcRenderer.sendSync('athena:translucency:support')
const hudWindowing = ipcRenderer.sendSync('athena:hud:windowing')
const hudNativeDrag = hudWindowing?.nativeDrag === true
const launchFlags = ipcRenderer.sendSync('athena:launch-flags')

contextBridge.exposeInMainWorld('athenaDesktop', {
  glassSupported: translucencySupport?.glass === true,
  translucencySupported: translucencySupport?.translucency === true,
  // Launch-flag fact: the app was started with --local, so the renderer may
  // show the local-models surfaces. Static for the window's lifetime.
  localModelsEnabled: launchFlags?.localModels === true,
  // Launch-flag fact: the Nous free tier is on for this launch
  // (ATHENA_GUEST_ONBOARDING=1 or --guest-onboarding). Read-only; the same
  // decision is stamped onto every backend the app spawns.
  guestOnboardingEnabled: launchFlags?.guestOnboarding === true,
  getConnection: (profile, opts) => ipcRenderer.invoke('athena:connection', profile, opts),
  // Registry-scoped backend resolution: { connectionId, profile } → descriptor.
  getConnectionFor: payload => ipcRenderer.invoke('athena:connection:for', payload),
  getProfileRoutes: profiles => ipcRenderer.invoke('athena:plugin-profile-routes', profiles),
  revalidateConnection: () => ipcRenderer.invoke('athena:connection:revalidate'),
  touchBackend: profile => ipcRenderer.invoke('athena:backend:touch', profile),
  getPoolLimits: () => ipcRenderer.invoke('athena:pool-limits:get'),
  setPoolLimits: limits => ipcRenderer.invoke('athena:pool-limits:set', limits),
  getGatewayWsUrl: profile => ipcRenderer.invoke('athena:gateway:ws-url', profile),
  // Registry-scoped fresh WS URL: { connectionId, profile } → result shape of
  // getGatewayWsUrl, minted against that connection's backend.
  getGatewayWsUrlFor: payload => ipcRenderer.invoke('athena:gateway:ws-url-for', payload),
  // Union agent roster across every registered connection.
  getAgentRoster: () => ipcRenderer.invoke('athena:agents:roster'),
  openSessionWindow: (sessionId, opts) => ipcRenderer.invoke('athena:window:openSession', sessionId, opts),
  openSessionInTerminal: (sessionId, opts) => ipcRenderer.invoke('athena:window:openInTerminal', sessionId, opts),
  openWindow: () => ipcRenderer.invoke('athena:window:openInstance'),
  openBrowserWindow: tabId => ipcRenderer.invoke('athena:window:openBrowser', tabId),
  onBrowserPopoutClosed: callback => {
    const listener = (_event, tabId) => callback(tabId)
    ipcRenderer.on('athena:browser-popout:closed', listener)

    return () => ipcRenderer.removeListener('athena:browser-popout:closed', listener)
  },
  claimAmbientCue: key => ipcRenderer.invoke('athena:ambient:claim', key),
  wakeIndicator: {
    getState: () => ipcRenderer.invoke('athena:wake-indicator:get'),
    setState: state => ipcRenderer.send('athena:wake-indicator:set', state),
    onState: callback => {
      const listener = (_event, state) => callback(state)
      ipcRenderer.on('athena:wake-indicator:state', listener)

      return () => ipcRenderer.removeListener('athena:wake-indicator:state', listener)
    }
  },
  chatOnboarding: {
    grow: request => ipcRenderer.send('athena:chat-onboarding:grow', request),
    soloBoot: () => ipcRenderer.send('athena:chat-onboarding:solo-boot')
  },
  introReveal: {
    open: (payload?: { hideMain?: boolean }) => ipcRenderer.invoke('athena:intro-reveal:open', payload),
    close: (payload?: { showMain?: boolean }) => ipcRenderer.invoke('athena:intro-reveal:close', payload),
    skip: () => ipcRenderer.send('athena:intro-reveal:skip'),
    ready: () => ipcRenderer.send('athena:intro-reveal:ready'),
    onSkip: callback => {
      const listener = () => callback()

      ipcRenderer.on('athena:intro-reveal:skip', listener)

      return () => ipcRenderer.removeListener('athena:intro-reveal:skip', listener)
    },
    onClosed: callback => {
      const listener = () => callback()

      ipcRenderer.on('athena:intro-reveal:closed', listener)

      return () => ipcRenderer.removeListener('athena:intro-reveal:closed', listener)
    }
  },
  petOverlay: {
    // Main renderer → main process: window lifecycle + drag. `request` is
    // `{ bounds, screen }`; resolves with the screen bounds it actually used.
    open: request => ipcRenderer.invoke('athena:pet-overlay:open', request),
    close: () => ipcRenderer.invoke('athena:pet-overlay:close'),
    setBounds: bounds => ipcRenderer.send('athena:pet-overlay:set-bounds', bounds),
    setIgnoreMouse: ignore => ipcRenderer.send('athena:pet-overlay:ignore-mouse', ignore),
    // Flip the overlay focusable (and focus it) while the composer needs keys.
    setFocusable: focusable => ipcRenderer.send('athena:pet-overlay:set-focusable', focusable),
    // Main renderer → overlay (forwarded by main): push the latest pet state.
    pushState: payload => ipcRenderer.send('athena:pet-overlay:state', payload),
    // Overlay → main renderer (forwarded by main): pop back in / composer submit.
    control: payload => ipcRenderer.send('athena:pet-overlay:control', payload),
    // Overlay subscribes to state pushes.
    onState: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('athena:pet-overlay:state', listener)

      return () => ipcRenderer.removeListener('athena:pet-overlay:state', listener)
    },
    // Main renderer subscribes to overlay control messages.
    onControl: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('athena:pet-overlay:control', listener)

      return () => ipcRenderer.removeListener('athena:pet-overlay:control', listener)
    }
  },
  // HUD mode: the chrome-free floating chat. A full app renderer (own gateway)
  // sized as a floating bar, so it mounts the real composer. Main owns the
  // window; `onChanged` keeps every window's toggle truthful.
  hud: {
    nativeDrag: hudNativeDrag,
    windowing: {
      clientPlacement: hudWindowing?.clientPlacement !== false,
      controlDrag: hudWindowing?.controlDrag === true,
      nativeDrag: hudNativeDrag,
      solid: hudWindowing?.solid === true,
      workspaceTransfer: hudWindowing?.workspaceTransfer === true
    },
    open: request => ipcRenderer.invoke('athena:hud:open', request),
    close: () => ipcRenderer.invoke('athena:hud:close'),
    setIgnoreMouse: ignore => ipcRenderer.send('athena:hud:ignore-mouse', ignore),
    beginMove: () => ipcRenderer.send('athena:hud:begin-move'),
    endMove: () => ipcRenderer.send('athena:hud:end-move'),
    moveBy: delta => ipcRenderer.send('athena:hud:move-by', delta),
    setWorkspaceTransfer: transferring => ipcRenderer.send('athena:hud:workspace-transfer', transferring),
    setBounds: bounds => ipcRenderer.send('athena:hud:set-bounds', bounds),
    resetLayout: () => ipcRenderer.invoke('athena:hud:reset-layout'),
    // Whether the band covers the window below the bar. Main pairs it with the
    // user's translucency setting to decide the native frost (macOS vibrancy /
    // Windows 11 DWM backdrop) — see hudFrostFor.
    setFrost: showing => ipcRenderer.invoke('athena:hud:frost', showing),
    // The HUD tells main which session it is on; main hands that back to the
    // app window when the HUD closes, so the app can re-home onto it.
    setSession: sessionId => ipcRenderer.send('athena:hud:session', sessionId),
    onGoto: callback => {
      const listener = (_event, sessionId) => callback(sessionId)
      ipcRenderer.on('athena:hud:goto', listener)

      return () => ipcRenderer.removeListener('athena:hud:goto', listener)
    },
    onChanged: callback => {
      const listener = (_event, state) => callback(state)
      ipcRenderer.on('athena:hud:changed', listener)

      return () => ipcRenderer.removeListener('athena:hud:changed', listener)
    },
    // Linux only, and silent elsewhere: where the cursor is, in page
    // coordinates, or null when it has left the window. Stands in for the
    // mousemove that `setIgnoreMouseEvents(true, { forward: true })` delivers on
    // macOS and Windows but not here.
    onCursor: callback => {
      const listener = (_event, point) => callback(point)
      ipcRenderer.on('athena:hud:cursor', listener)

      return () => ipcRenderer.removeListener('athena:hud:cursor', listener)
    },
    // Main's game-overlay watch: whether a fullscreen app (a game) is under
    // the HUD, so the renderer can step back to the low-opacity overlay
    // treatment while one owns the screen.
    onGameOverlay: callback => {
      const listener = (_event, state) => callback(state)
      ipcRenderer.on('athena:hud:game-overlay', listener)

      return () => ipcRenderer.removeListener('athena:hud:game-overlay', listener)
    }
  },
  // Quick Entry: the global-hotkey mini composer window. Main owns the OS
  // shortcut + the persisted preference; the quick window only captures text
  // and hands it back, and the primary renderer submits it through the normal
  // prompt path.
  quickEntry: {
    getSettings: () => ipcRenderer.invoke('athena:quick-entry:settings:get'),
    setSettings: patch => ipcRenderer.invoke('athena:quick-entry:settings:set', patch),
    submit: payload => ipcRenderer.send('athena:quick-entry:submit', payload),
    dismiss: () => ipcRenderer.send('athena:quick-entry:dismiss'),
    // Primary renderer → main → quick window: gateway connection state + the
    // recent-session options the target picker offers. Main caches the latest
    // payload so a freshly spawned quick window starts from truth.
    pushState: payload => ipcRenderer.send('athena:quick-entry:state', payload),
    // Quick window subscribes to those pushes.
    onState: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('athena:quick-entry:state', listener)

      return () => ipcRenderer.removeListener('athena:quick-entry:state', listener)
    },
    // Main → primary renderer: a submit captured by the quick window.
    onSubmit: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('athena:quick-entry:submit', listener)

      return () => ipcRenderer.removeListener('athena:quick-entry:submit', listener)
    },
    // Main → quick window: you were just summoned (reset draft + refocus).
    onShown: callback => {
      const listener = () => callback()
      ipcRenderer.on('athena:quick-entry:shown', listener)

      return () => ipcRenderer.removeListener('athena:quick-entry:shown', listener)
    }
  },
  getBootProgress: () => ipcRenderer.invoke('athena:boot-progress:get'),
  getConnectionConfig: profile => ipcRenderer.invoke('athena:connection-config:get', profile),
  saveConnectionConfig: payload => ipcRenderer.invoke('athena:connection-config:save', payload),
  applyConnectionConfig: payload => ipcRenderer.invoke('athena:connection-config:apply', payload),
  testConnectionConfig: payload => ipcRenderer.invoke('athena:connection-config:test', payload),
  // Opt-in OS-keychain encryption for stored gateway secrets (default off —
  // see secret-storage-policy.ts). get never touches the OS keychain.
  getSecretStorageEncryption: () => ipcRenderer.invoke('athena:secret-storage:get'),
  setSecretStorageEncryption: (on: boolean) => ipcRenderer.invoke('athena:secret-storage:set', on),
  // v2 multi-connection registry: named agent sources (local / remote / cloud / ssh).
  connections: {
    list: () => ipcRenderer.invoke('athena:connections:list'),
    save: payload => ipcRenderer.invoke('athena:connections:save', payload),
    remove: id => ipcRenderer.invoke('athena:connections:remove', id),
    setPrimary: id => ipcRenderer.invoke('athena:connections:set-primary', id),
    setLaunchMode: mode => ipcRenderer.invoke('athena:connections:set-launch-mode', mode),
    setLastUsed: id => ipcRenderer.invoke('athena:connections:set-last-used', id),
    test: id => ipcRenderer.invoke('athena:connections:test', id),
    updateManaged: id => ipcRenderer.invoke('athena:connections:update-managed', id),
    // Fan out `athena update` to every eligible registered connection.
    // Optional excludeIds skips rows the caller updates through another path.
    updateAll: options => ipcRenderer.invoke('athena:connections:update-all', options),
    // Registry lifecycle push (main → renderer): a connection was removed or
    // materially edited, so secondaries scoped to it must be disposed (and,
    // for edits, re-dialed at the new target).
    onChanged: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('athena:connections:changed', listener)

      return () => ipcRenderer.removeListener('athena:connections:changed', listener)
    }
  },
  sshConfigHosts: () => ipcRenderer.invoke('athena:ssh-config:hosts'),
  sshResolveHost: host => ipcRenderer.invoke('athena:ssh-config:resolve', host),
  probeConnectionConfig: remoteUrl => ipcRenderer.invoke('athena:connection-config:probe', remoteUrl),
  oauthLoginConnectionConfig: remoteUrl => ipcRenderer.invoke('athena:connection-config:oauth-login', remoteUrl),
  oauthLogoutConnectionConfig: remoteUrl => ipcRenderer.invoke('athena:connection-config:oauth-logout', remoteUrl),
  // Athena Cloud: one portal login powers discovery + silent per-agent sign-in
  // (cloud-auto-discovery Phase 3).
  cloud: {
    status: () => ipcRenderer.invoke('athena:cloud:status'),
    login: () => ipcRenderer.invoke('athena:cloud:login'),
    logout: () => ipcRenderer.invoke('athena:cloud:logout'),
    discover: org => ipcRenderer.invoke('athena:cloud:discover', org),
    agentSignIn: dashboardUrl => ipcRenderer.invoke('athena:cloud:agent-sign-in', dashboardUrl)
  },
  profile: {
    get: () => ipcRenderer.invoke('athena:profile:get'),
    remember: name => ipcRenderer.invoke('athena:profile:remember', name),
    set: name => ipcRenderer.invoke('athena:profile:set', name)
  },
  api: request => ipcRenderer.invoke('athena:api', request),
  notify: payload => ipcRenderer.invoke('athena:notify', payload),
  requestMicrophoneAccess: () => ipcRenderer.invoke('athena:requestMicrophoneAccess'),
  readWindowBelow: () => ipcRenderer.invoke('athena:window:readBelow'),
  readFileDataUrl: filePath => ipcRenderer.invoke('athena:readFileDataUrl', filePath),
  readFileDataUrlForAttach: filePath => ipcRenderer.invoke('athena:readFileDataUrlForAttach', filePath),
  dataUrlReadMax: {
    get: () => ipcRenderer.invoke('athena:data-url-read-max:get'),
    set: maxMb => ipcRenderer.invoke('athena:data-url-read-max:set', maxMb)
  },
  readFileText: filePath => ipcRenderer.invoke('athena:readFileText', filePath),
  readPluginSource: (filePath: string) => ipcRenderer.invoke('athena:readPluginSource', filePath),
  selectPaths: options => ipcRenderer.invoke('athena:selectPaths', options),
  selectSavePath: options => ipcRenderer.invoke('athena:selectSavePath', options),
  writeClipboard: text => ipcRenderer.invoke('athena:writeClipboard', text),
  readClipboard: () => ipcRenderer.invoke('athena:readClipboard'),
  saveGatewayFile: payload => ipcRenderer.invoke('athena:saveGatewayFile', payload),
  saveImageFromUrl: url => ipcRenderer.invoke('athena:saveImageFromUrl', url),
  contextMenuEdit: command => ipcRenderer.invoke('athena:context-menu:edit', command),
  contextMenuCopyImage: () => ipcRenderer.invoke('athena:context-menu:copy-image'),
  contextMenuSpellcheck: action => ipcRenderer.invoke('athena:context-menu:spellcheck', action),
  contextMenuGuestAddWord: payload => ipcRenderer.invoke('athena:context-menu:guest-add-word', payload),
  onContextMenuSpellcheck: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('athena:context-menu-spellcheck', listener)

    return () => ipcRenderer.removeListener('athena:context-menu-spellcheck', listener)
  },
  saveImageBuffer: (data, ext, name) => ipcRenderer.invoke('athena:saveImageBuffer', { data, ext, name }),
  capturePreview: payload => ipcRenderer.invoke('athena:capturePreview', payload),
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
  watchDirectory: dir => ipcRenderer.invoke('athena:watchDirectory', dir),
  stopPreviewFileWatch: id => ipcRenderer.invoke('athena:stopPreviewFileWatch', id),
  setActiveWork: payload => ipcRenderer.send('athena:active-work', payload),
  setTitleBarTheme: payload => ipcRenderer.send('athena:titlebar-theme', payload),
  setNativeTheme: mode => ipcRenderer.send('athena:native-theme', mode),
  setTranslucency: payload => ipcRenderer.send('athena:translucency', payload),
  setKeepAwake: on => ipcRenderer.send('athena:keep-awake', on),
  setDisableF12: blocked => ipcRenderer.send('athena:devtools:disable-f12', blocked),
  setPreviewShortcutActive: active => ipcRenderer.send('athena:previewShortcutActive', Boolean(active)),
  openExternal: url => ipcRenderer.invoke('athena:openExternal', url),
  mcpOauth: {
    // One-shot loopback listener for MCP OAuth against remote backends: bind
    // on this machine, hand redirectUri to mcp.servers.oauth.start, then wait
    // for the provider redirect and relay code/state via oauth.callback.
    listen: () => ipcRenderer.invoke('athena:mcp-oauth:listen'),
    wait: (id, timeoutMs) => ipcRenderer.invoke('athena:mcp-oauth:wait', id, timeoutMs),
    cancel: id => ipcRenderer.invoke('athena:mcp-oauth:cancel', id)
  },
  openPreviewInBrowser: url => ipcRenderer.invoke('athena:openPreviewInBrowser', url),
  reachPreviewUrl: url => ipcRenderer.invoke('athena:preview:reach', url),
  setActiveConnectionRoute: route => ipcRenderer.send('athena:connection:active-route', route),
  fetchLinkTitle: url => ipcRenderer.invoke('athena:fetchLinkTitle', url),
  resolveFavicon: url => ipcRenderer.invoke('athena:resolveFavicon', url),
  sanitizeWorkspaceCwd: cwd => ipcRenderer.invoke('athena:workspace:sanitize', cwd),
  settings: {
    getDefaultProjectDir: () => ipcRenderer.invoke('athena:setting:defaultProjectDir:get'),
    setDefaultProjectDir: dir => ipcRenderer.invoke('athena:setting:defaultProjectDir:set', dir),
    pickDefaultProjectDir: () => ipcRenderer.invoke('athena:setting:defaultProjectDir:pick')
  },
  zoom: {
    // Current zoom of this window, as { level, percent }.
    get: () => ipcRenderer.invoke('athena:zoom:get'),
    // Synchronous zoom factor (1 = 100%). Coordinate math needs it in the
    // same tick as the event it converts, so no IPC round-trip here.
    factor: () => webFrame.getZoomFactor(),
    setPercent: percent => ipcRenderer.send('athena:zoom:set-percent', percent),
    // Fires on every zoom change, including the Ctrl/Cmd +/-/0 shortcuts,
    // so the settings UI can stay in sync with the keyboard.
    onChanged: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('athena:zoom:changed', listener)

      return () => ipcRenderer.removeListener('athena:zoom:changed', listener)
    }
  },
  revealLogs: () => ipcRenderer.invoke('athena:logs:reveal'),
  getRecentLogs: () => ipcRenderer.invoke('athena:logs:recent'),
  // Fire-and-forget: persists a renderer error-boundary catch (with component
  // stack) to desktop.log so crashes survive the window (#79428).
  reportRendererError: report => ipcRenderer.send('athena:logs:renderer-error', report),
  readDir: dirPath => ipcRenderer.invoke('athena:fs:readDir', dirPath),
  gitRoot: startPath => ipcRenderer.invoke('athena:fs:gitRoot', startPath),
  revealPath: targetPath => ipcRenderer.invoke('athena:fs:reveal', targetPath),
  openDir: dirPath => ipcRenderer.invoke('athena:fs:openDir', dirPath),
  desktopPluginsRoot: () => ipcRenderer.invoke('athena:fs:desktopPluginsRoot'),
  reconcileDesktopPlugins: () => ipcRenderer.invoke('athena:fs:reconcileDesktopPlugins'),
  logsRoot: () => ipcRenderer.invoke('athena:fs:logsRoot'),
  renamePath: (targetPath, newName) => ipcRenderer.invoke('athena:fs:rename', targetPath, newName),
  writeTextFile: (filePath, content) => ipcRenderer.invoke('athena:fs:writeText', filePath, content),
  trashPath: targetPath => ipcRenderer.invoke('athena:fs:trash', targetPath),
  git: {
    worktreeList: repoPath => ipcRenderer.invoke('athena:git:worktreeList', repoPath),
    worktreeAdd: (repoPath, options) => ipcRenderer.invoke('athena:git:worktreeAdd', repoPath, options),
    worktreeRemove: (repoPath, worktreePath, options) =>
      ipcRenderer.invoke('athena:git:worktreeRemove', repoPath, worktreePath, options),
    branchSwitch: (repoPath, branch) => ipcRenderer.invoke('athena:git:branchSwitch', repoPath, branch),
    branchList: repoPath => ipcRenderer.invoke('athena:git:branchList', repoPath),
    baseBranchList: repoPath => ipcRenderer.invoke('athena:git:baseBranchList', repoPath),
    repoStatus: repoPath => ipcRenderer.invoke('athena:git:repoStatus', repoPath),
    fileDiff: (repoPath, filePath) => ipcRenderer.invoke('athena:git:fileDiff', repoPath, filePath),
    scanRepos: (roots, options) => ipcRenderer.invoke('athena:git:scanRepos', roots, options),
    review: {
      list: (repoPath, scope, baseRef) => ipcRenderer.invoke('athena:git:review:list', repoPath, scope, baseRef),
      diff: (repoPath, filePath, scope, baseRef, staged) =>
        ipcRenderer.invoke('athena:git:review:diff', repoPath, filePath, scope, baseRef, staged),
      stage: (repoPath, filePath) => ipcRenderer.invoke('athena:git:review:stage', repoPath, filePath),
      unstage: (repoPath, filePath) => ipcRenderer.invoke('athena:git:review:unstage', repoPath, filePath),
      revert: (repoPath, filePath) => ipcRenderer.invoke('athena:git:review:revert', repoPath, filePath),
      revParse: (repoPath, ref) => ipcRenderer.invoke('athena:git:review:revParse', repoPath, ref),
      commit: (repoPath, message, push) => ipcRenderer.invoke('athena:git:review:commit', repoPath, message, push),
      commitContext: repoPath => ipcRenderer.invoke('athena:git:review:commitContext', repoPath),
      push: repoPath => ipcRenderer.invoke('athena:git:review:push', repoPath),
      shipInfo: repoPath => ipcRenderer.invoke('athena:git:review:shipInfo', repoPath),
      prList: (repoPath, branches, numbers) =>
        ipcRenderer.invoke('athena:git:review:prList', repoPath, branches, numbers),
      fetchPrComment: (repoPath, url) => ipcRenderer.invoke('athena:git:review:fetchPrComment', repoPath, url),
      createPr: repoPath => ipcRenderer.invoke('athena:git:review:createPr', repoPath)
    }
  },
  terminal: {
    attach: id => ipcRenderer.invoke('athena:terminal:attach', id),
    cwd: id => ipcRenderer.invoke('athena:terminal:cwd', id),
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
  onPreviewNav: callback => {
    const listener = (_event, command) => callback(command)
    ipcRenderer.on('athena:preview-nav', listener)

    return () => ipcRenderer.removeListener('athena:preview-nav', listener)
  },
  onOpenFolderRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('athena:open-folder-requested', listener)

    return () => ipcRenderer.removeListener('athena:open-folder-requested', listener)
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
  probePluginRepo: payload => ipcRenderer.invoke('athena:plugin:probe', payload),
  installDesktopPlugin: payload => ipcRenderer.invoke('athena:plugin:installDesktop', payload),
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
  onNotificationActivate: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('athena:notification-activate', listener)

    return () => ipcRenderer.removeListener('athena:notification-activate', listener)
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
  // Soft gateway-mode apply finished tearing down the primary backend. Renderer
  // should wipe session lists + re-dial without a window reload.
  onConnectionApplied: callback => {
    const listener = () => callback()
    ipcRenderer.on('athena:connection:applied', listener)

    return () => ipcRenderer.removeListener('athena:connection:applied', listener)
  },
  onPowerResume: callback => {
    const listener = () => callback()
    ipcRenderer.on('athena:power-resume', listener)

    return () => ipcRenderer.removeListener('athena:power-resume', listener)
  },
  // AC ↔ battery transitions; renderers slow their backstop polls on battery.
  getOnBattery: () => ipcRenderer.invoke('athena:power-battery:get'),
  onBatteryChanged: callback => {
    const listener = (_event, onBattery) => callback(Boolean(onBattery))
    ipcRenderer.on('athena:power-battery', listener)

    return () => ipcRenderer.removeListener('athena:power-battery', listener)
  },
  onBootProgress: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('athena:boot-progress', listener)

    return () => ipcRenderer.removeListener('athena:boot-progress', listener)
  },
  // First-launch bootstrap progress -- emitted by the install.ps1 stage
  // runner in main.ts (apps/desktop/electron/bootstrap-runner.ts).
  // Renderer's install overlay subscribes to live events and queries the
  // current snapshot via getBootstrapState() to recover after a devtools
  // reload mid-bootstrap.
  getBootstrapState: () => ipcRenderer.invoke('athena:bootstrap:get'),
  continueBootstrapLocal: () => ipcRenderer.invoke('athena:bootstrap:continue-local'),
  recycleBackend: profile => ipcRenderer.invoke('athena:backend:recycle', profile),
  resetBootstrap: () => ipcRenderer.invoke('athena:bootstrap:reset'),
  repairBootstrap: () => ipcRenderer.invoke('athena:bootstrap:repair'),
  cancelBootstrap: () => ipcRenderer.invoke('athena:bootstrap:cancel'),
  onBootstrapEvent: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('athena:bootstrap:event', listener)

    return () => ipcRenderer.removeListener('athena:bootstrap:event', listener)
  },
  getVersion: () => ipcRenderer.invoke('athena:version'),
  relaunchApp: () => ipcRenderer.invoke('athena:app:relaunch'),
  getMachineProfile: () => ipcRenderer.invoke('athena:machine:profile'),
  getRemoteDisplayReason: () => ipcRenderer.invoke('athena:get-remote-display-reason'),
  uninstall: {
    summary: () => ipcRenderer.invoke('athena:uninstall:summary'),
    run: mode => ipcRenderer.invoke('athena:uninstall:run', { mode })
  },
  updates: {
    check: opts => ipcRenderer.invoke('athena:updates:check', opts),
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
  },
  // Find-in-page (Ctrl/Cmd+F): delegates to Electron's
  // webContents.findInPage on the IPC sender's window so a Cmd+F pressed
  // in a secondary session window searches THAT window, not the primary.
  // `onFoundInPage` returns the unsubscribe fn; the renderer wires it via
  // `initFindInPageListener` in store/find-in-page.ts and tears it down
  // when the FindBar unmounts.
  findInPage: (query, options) => ipcRenderer.invoke('athena:find-in-page', query, options),
  stopFindInPage: () => ipcRenderer.invoke('athena:stop-find-in-page'),
  onFoundInPage: callback => {
    const listener = (_event, result) => callback(result)
    ipcRenderer.on('athena:found-in-page', listener)

    return () => ipcRenderer.removeListener('athena:found-in-page', listener)
  },
  // Main-process `before-input-event` forwards Ctrl/Cmd+F here so renderer
  // can open the FindBar even when the GTK compositor has already grabbed
  // the chord at the windowing layer (#81727).
  onOpenFindBarRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('athena:open-find-bar', listener)

    return () => ipcRenderer.removeListener('athena:open-find-bar', listener)
  }
})
