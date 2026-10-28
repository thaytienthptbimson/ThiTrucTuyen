'use strict';
/*
 * Vỏ Electron cho bản Windows (.exe).
 * Mã nguồn web nằm trong thư mục www/ và được phục vụ qua địa chỉ app://local/
 * để fetch('du-lieu.json'), localStorage, IndexedDB... hoạt động như trên web thật
 * (mở thẳng file:// thì fetch tệp JSON bị chặn).
 */
const { app, BrowserWindow, Menu, protocol, net, shell } = require('electron');
const path = require('path');
const { pathToFileURL } = require('url');

const WWW = path.join(__dirname, 'www');
const ICON = path.join(__dirname, 'build', 'icon.png');

protocol.registerSchemesAsPrivileged([
  {
    scheme: 'app',
    privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true, stream: true },
  },
]);

function resolveRequest(requestUrl) {
  let rel;
  try {
    rel = decodeURIComponent(new URL(requestUrl).pathname);
  } catch (e) {
    return null;
  }
  if (rel.endsWith('/')) rel += 'index.html';
  const full = path.normalize(path.join(WWW, rel));
  if (full !== WWW && !full.startsWith(WWW + path.sep)) return null; // chặn ../
  return full;
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 800,
    minHeight: 560,
    show: false,
    backgroundColor: '#ffffff',
    autoHideMenuBar: true,
    icon: ICON,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      spellcheck: false,
    },
  });

  win.once('ready-to-show', () => {
    win.maximize();
    win.show();
  });

  // Liên kết ra internet mở bằng trình duyệt; cửa sổ in/xuất báo cáo của ứng dụng vẫn mở bình thường.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^(https?:|mailto:)/i.test(url)) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow', overrideBrowserWindowOptions: { autoHideMenuBar: true, icon: ICON } };
  });
  win.webContents.on('will-navigate', (event, url) => {
    if (/^https?:/i.test(url)) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  win.loadURL('app://local/index.html');
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => {
    const win = BrowserWindow.getAllWindows()[0];
    if (win) {
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  });

  app.whenReady().then(() => {
    Menu.setApplicationMenu(null);

    protocol.handle('app', async (request) => {
      const file = resolveRequest(request.url);
      if (!file) return new Response('Forbidden', { status: 403 });
      try {
        return await net.fetch(pathToFileURL(file).toString());
      } catch (e) {
        return new Response('Not found', { status: 404 });
      }
    });

    createWindow();
    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
  });

  app.on('window-all-closed', () => app.quit());
}
