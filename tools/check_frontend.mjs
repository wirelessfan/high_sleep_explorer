// 前端模块语法与导入检查（Node 侧，不依赖浏览器）
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = process.argv[2] || '.';
const files = [
  'web/js/app.js',
  'web/js/api.js',
  'web/js/ui.js',
  'web/js/router.js',
  'web/js/boss.js',
  'web/js/views/home.js',
  'web/js/views/subjects.js',
  'web/js/views/topic.js',
  'web/js/views/section.js',
  'web/js/views/album.js',
  'web/js/views/me.js',
];

let bad = 0;
for (const f of files) {
  const abs = path.resolve(root, f);
  try {
    // 仅做语法检查：读源码 → 用 SourceTextModule 之外的简单方式
    const src = fs.readFileSync(abs, 'utf8');
    // 检查静态与动态 import 的路径是否都存在
    const patterns = [
      /from\s+['"](\.[^'"]+)['"]/g,
      /import\(\s*['"](\.[^'"]+)['"]\s*\)/g,
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
    await import(pathToFileURL(abs).href).catch((e) => {
      // DOM 相关运行时错误可忽略，但语法/导入错误必须报
      if (/document is not defined|window is not defined|localStorage/.test(e.message)) return;
      throw e;
    });
    console.log('OK   ', f);
  } catch (e) {
    console.log('FAIL ', f, '->', e.message);
    bad++;
  }
}
console.log(bad ? `\n${bad} 个文件有问题` : '\n全部模块检查通过');
process.exit(bad ? 1 : 0);
