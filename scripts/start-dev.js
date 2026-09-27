const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const rootDir = path.resolve(__dirname, '..');
const frontendDir = path.join(rootDir, 'frontend');
const backendDir = path.join(rootDir, 'backend');

console.log('\x1b[36m%s\x1b[0m', '=====================================================');
console.log('\x1b[36m%s\x1b[0m', '   FieryVision AI — Local Development Runner         ');
console.log('\x1b[36m%s\x1b[0m', '=====================================================');
console.log('Starting Backend  -> http://localhost:8000 (Swagger: /docs)');
console.log('Starting Frontend -> http://localhost:5173');
console.log('\x1b[90m%s\x1b[0m', 'Press Ctrl+C to stop both processes.\n');

const isWin = process.platform === 'win32';
const npmCmd = isWin ? 'npm.cmd' : 'npm';

// Prefer backend/venv python if it exists to guarantee matching dependencies
const venvPython = isWin
  ? path.join(backendDir, 'venv', 'Scripts', 'python.exe')
  : path.join(backendDir, 'venv', 'bin', 'python');
const pythonCmd = fs.existsSync(venvPython) ? venvPython : (isWin ? 'python' : 'python3');

// Configure reload directories so uvicorn does NOT watch backend/venv, node_modules, or cache
const mlDir = path.join(rootDir, 'ml');
const uvicornArgs = [
  '-m', 'uvicorn', 'main:app',
  '--reload',
  '--reload-dir', 'app',
];
if (fs.existsSync(mlDir)) {
  uvicornArgs.push('--reload-dir', path.relative(backendDir, mlDir));
}
uvicornArgs.push(
  '--reload-exclude', 'venv',
  '--reload-exclude', '.venv',
  '--reload-exclude', '*/venv/*',
  '--reload-exclude', '*site-packages*',
  '--reload-exclude', 'node_modules',
  '--reload-exclude', 'data/cache',
  '--port', '8000'
);

// Start Backend
const backend = spawn(pythonCmd, uvicornArgs, {
  cwd: backendDir,
  stdio: 'pipe',
  env: { ...process.env, PYTHONUNBUFFERED: '1' }
});

backend.stdout.on('data', (data) => {
  process.stdout.write(`\x1b[35m[backend]\x1b[0m ${data}`);
});

backend.stderr.on('data', (data) => {
  process.stderr.write(`\x1b[35m[backend]\x1b[0m ${data}`);
});

// Start Frontend
const frontend = spawn(npmCmd, ['run', 'dev'], {
  cwd: frontendDir,
  stdio: 'pipe',
});

frontend.stdout.on('data', (data) => {
  process.stdout.write(`\x1b[36m[frontend]\x1b[0m ${data}`);
});

frontend.stderr.on('data', (data) => {
  process.stderr.write(`\x1b[36m[frontend]\x1b[0m ${data}`);
});

function cleanup() {
  console.log('\n\x1b[33mShutting down FieryVision processes...\x1b[0m');
  try {
    if (isWin) {
      if (backend.pid) spawn('taskkill', ['/pid', backend.pid.toString(), '/f', '/t']);
      if (frontend.pid) spawn('taskkill', ['/pid', frontend.pid.toString(), '/f', '/t']);
    } else {
      backend.kill('SIGINT');
      frontend.kill('SIGINT');
    }
  } catch (e) {
    // ignore shutdown errors
  }
  process.exit();
}

process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);
