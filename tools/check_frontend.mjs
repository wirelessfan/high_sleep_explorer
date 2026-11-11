// 前端模块检查（Node 侧，不依赖浏览器）
//
// 做两件事：
//   1. 静态校验相对 import（含动态 import()）的路径是否真实存在
//   2. 用 node --check 校验每个文件的语法
//
// 刻意不在 Node 里 import 这些模块：它们依赖 document/window，
// 顶层副作用（如 app.js 的 boot()）会在无 DOM 环境里抛错，
// 那样检查的就不是语法，而是「能不能在 Node 里跑」。
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import os from 'node:os';

const root = process.argv[2] || '.';

function collect(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...collect(p));
    else if (entry.name.endsWith('.js')) out.push(p);
  }
  return out;
}

const jsDir = path.resolve(root, 'web/js');
if (!fs.existsSync(jsDir)) {
  console.error(`找不到前端目录: ${jsDir}`);
  process.exit(1);
}
const files = collect(jsDir).sort();

let bad = 0;
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'fe-check-'));

for (const abs of files) {
  const rel = path.relative(root, abs).split(path.sep).join('/');
  try {
    const src = fs.readFileSync(abs, 'utf8');

    // 1) 相对导入目标必须存在
    const patterns = [
      /from\s+['"](\.[^'"]+)['"]/g,          // import x from './y.js'
      /import\(\s*['"](\.[^'"]+)['"]\s*\)/g, // await import('./y.js')
    ];
    for (const re of patterns) {
      let m;
      while ((m = re.exec(src))) {
        const target = path.resolve(path.dirname(abs), m[1]);
        if (!fs.existsSync(target)) {
          throw new Error(`导入目标不存在: ${m[1]}`);
        }
      }
    }

    // 2) 语法检查（复制成 .mjs 让 node 按 ESM 解析）
    const tmp = path.join(tmpDir, `${path.basename(abs, '.js')}-${files.indexOf(abs)}.mjs`);
    fs.writeFileSync(tmp, src, 'utf8');
    try {
      execFileSync(process.execPath, ['--check', tmp], { stdio: 'pipe' });
    } catch (e) {
      const msg = (e.stderr || Buffer.from('')).toString().split('\n').slice(0, 3).join(' ').trim();
      throw new Error(`语法错误: ${msg}`);
    }

    console.log('OK   ', rel);
  } catch (e) {
    console.log('FAIL ', rel, '->', e.message);
    bad++;
  }
}

fs.rmSync(tmpDir, { recursive: true, force: true });
console.log(bad ? `\n${bad} 个文件有问题` : `\n全部模块检查通过（${files.length} 个文件）`);
process.exit(bad ? 1 : 0);
