#!/usr/bin/env node

const { spawn, execSync } = require('child_process');
const path = require('path');

// 获取项目根目录
const projectRoot = path.resolve(__dirname, '..');

// 动态查找 Python 可执行文件
// 按优先级顺序尝试常见的 Python 命令
// 用户可以通过设置 PYTHON_EXE 环境变量来指定特定路径
function findPython() {
  // 首先检查环境变量
  if (process.env.PYTHON_EXE) {
    return process.env.PYTHON_EXE;
  }

  // 常见的 Python 命令（按优先级）
  const possibleCommands = [
    'python',   // 最常见
    'python3',  // Linux/Mac
    'py',       // Windows launcher
    'python3.12',
    'python3.13',
  ];

  for (const cmd of possibleCommands) {
    try {
      execSync(`"${cmd}" --version`, { stdio: 'ignore' });
      console.log(`Found Python: ${cmd}`);
      return cmd;
    } catch (e) {
      continue;
    }
  }
  throw new Error('Python not found. Please install Python or add it to PATH.');
}

const pythonExe = findPython();
const serverModule = 'mcp_server.simple_http_mcp_server';

console.log('Starting GELab MCP Server...');
console.log('Python:', pythonExe);
console.log('Project root:', projectRoot);

// 设置环境变量
const env = {
  ...process.env,
  PYTHONPATH: projectRoot
};

// 启动 Python 服务器
const pythonProcess = spawn(pythonExe, ['-m', serverModule], {
  cwd: projectRoot,
  stdio: 'inherit',
  shell: true,
  env: env
});

pythonProcess.on('error', (error) => {
  console.error('Failed to start Python server:', error);
  process.exit(1);
});

pythonProcess.on('close', (code) => {
  console.log(`Python server exited with code ${code}`);
  process.exit(code);
});

// 向前传递信号
process.on('SIGINT', () => {
  console.log('\nReceived SIGINT, shutting down...');
  pythonProcess.kill('SIGINT');
});

process.on('SIGTERM', () => {
  console.log('\nReceived SIGTERM, shutting down...');
  pythonProcess.kill('SIGTERM');
});
