#!/usr/bin/env node
/*
 * 接线测试：HTML 和 JS 之间的引用对不对得上。
 *
 * 这个项目所有「点了没反应」和「永远显示假数据」的 bug 都是同一类：
 *   - HTML 写 onclick="switchView(...)"，但 switchView 根本没定义 → 点下去才崩
 *   - HTML 里有 id="rep-tot">1420<，JS 从没绑过它 → 永远显示 1420，没人发现
 *   - JS 写 getElementById('xxx')，HTML 里没有这个 id → 静默拿到 null
 *
 * 纯静态扫描，不跑浏览器，秒级完成。
 */
const fs = require("fs");
const path = require("path");
const SITE = process.env.SITE_DIR || path.resolve(__dirname, "..");
const src = fs.readFileSync(path.join(SITE, "index.html"), "utf8");

// 把所有 <script> 块拼成 js，其余（包括 </script> 之后的部分）全算 html。
// 只取「第一个 script 之前」会漏掉写在脚本后面的内联事件。
let js = "", html = "";
{
  let last = 0;
  for (const m of src.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) {
    html += src.slice(last, m.index);
    js += "\n" + m[1];
    last = m.index + m[0].length;
  }
  html += src.slice(last);
}

let bad = 0, ok = 0;
const fail = (msg) => { bad++; console.log("  FAIL " + msg); };
const pass = (msg) => { ok++; console.log("  ok   " + msg); };

/* ---------- 1. HTML 里引用的函数，JS 必须定义 ---------- */
console.log("\n=== 1. 内联事件引用的函数是否都存在 ===");
const defined = new Set();
for (const m of js.matchAll(/(?:^|\n)\s*(?:async\s+)?function\s+(\w+)\s*\(/g)) defined.add(m[1]);
for (const m of js.matchAll(/(?:^|\n)\s*(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\(|function)/g)) defined.add(m[1]);

// 只看「裸的全局函数调用」：前面不是点号（排除 event.preventDefault()、el.click()），
// 也不是语言关键字（if/for/return…）和浏览器内建。
const SKIP = new Set(["if","for","while","switch","return","typeof","catch","function",
                      "alert","confirm","prompt","print","open","close","setTimeout",
                      "parseInt","parseFloat","String","Number","Boolean","Array","Object","JSON"]);
const called = new Map();            // fnName -> 出现次数
for (const m of html.matchAll(/on\w+\s*=\s*"([^"]*)"/g)) {
  for (const f of m[1].matchAll(/(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(/g)) {
    if (!SKIP.has(f[1])) called.set(f[1], (called.get(f[1]) || 0) + 1);
  }
}
const missing = [...called.keys()].filter(f => !defined.has(f));
if (missing.length) missing.forEach(f => fail(`HTML 调用 ${f}() 共 ${called.get(f)} 处，但 JS 里没有定义`));
else pass(`${called.size} 个被内联事件引用的函数全部有定义`);

/* ---------- 2. JS 抓的 id，HTML 里必须有 ---------- */
console.log("\n=== 2. getElementById 的 id 是否都存在 ===");
const htmlIds = new Set([...src.matchAll(/\bid\s*=\s*"([\w-]+)"/g)].map(m => m[1]));
const grabbed = new Set([...js.matchAll(/getElementById\(\s*['"]([\w-]+)['"]\s*\)/g)].map(m => m[1]));
const ghosts = [...grabbed].filter(id => !htmlIds.has(id));
if (ghosts.length) ghosts.forEach(id => fail(`JS 抓 #${id}，但 HTML 里没有这个 id（会静默拿到 null）`));
else pass(`${grabbed.size} 个被 JS 抓取的 id 在 HTML 里都存在`);

/* ---------- 3. 带数字的 id：要么被 JS 更新，要么是写死的假数据 ---------- */
console.log("\n=== 3. 有没有「永远不会更新的数字」（1420 那类）===");
const suspicious = [];
for (const m of src.matchAll(/\bid\s*=\s*"([\w-]+)"[^>]*>\s*([^<]{1,16}?)\s*</g)) {
  const [, id, text] = m;
  if (!/^[\d,.%]+$/.test(text.trim())) continue;       // 只看纯数字内容
  if (grabbed.has(id)) continue;                        // JS 更新过，没问题
  if (/querySelector\(['"]#" ?\+|setAttribute/.test(js)) { /* 动态写法，忽略 */ }
  suspicious.push({ id, text: text.trim() });
}
if (suspicious.length) suspicious.forEach(x => fail(`#${x.id} 写死着「${x.text}」，JS 从未更新它`));
else pass("没有发现写死且永不更新的数字");

/* ---------- 3b. 写死的进度条（style="width:NN%" 但 JS 从不更新）---------- */
console.log("\n=== 3b. 有没有写死的进度条 ===");
const fakeBars = [];
for (const m of src.matchAll(/\bid\s*=\s*"([\w-]+)"[^>]*style\s*=\s*"[^"]*width:\s*(\d+)%/g)) {
  const [, id, w] = m;
  if (grabbed.has(id)) continue;                 // JS 用字面量抓过
  // 也认动态拼接：getElementById("prog-" + cat) 这种
  const prefix = id.replace(/[^a-z-]*$/i, "");
  if (prefix.length > 3 && new RegExp('getElementById\\(\\s*["\'`]' + prefix).test(js)) continue;
  if (w === "0" || w === "100") continue;        // 0/100 多半是占位或满格
  fakeBars.push({ id, w });
}
if (fakeBars.length) fakeBars.forEach(x => fail(`#${x.id} 的进度条写死在 ${x.w}%，JS 从未更新它`));
else pass("没有发现写死的进度条");

/* ---------- 3c. 界面承诺的快捷键是否真的有人监听 ---------- */
console.log("\n=== 3c. 界面写的快捷键是否真的实现了 ===");
const promised = new Set();
for (const m of html.matchAll(/\[([A-Za-z]|Alt\+[A-Za-z]|Esc|Shift\+[A-Za-z])\]/g)) promised.add(m[1]);
const hasKeydown = /addEventListener\(\s*["']keydown["']/.test(js);
if (!promised.size) pass("界面没有承诺快捷键");
else if (!hasKeydown) fail(`界面写着快捷键 ${[...promised].join(" / ")}，但全文件没有任何 keydown 监听`);
else {
  const unhandled = [...promised].filter(k => {
    if (k.startsWith("Alt+")) return !new RegExp("altKey").test(js);
    if (k === "Esc") return !/["']Escape["']/.test(js);
    return !new RegExp(`["']${k}["']|toUpperCase\\(\\)`, "i").test(js);
  });
  if (unhandled.length) fail(`界面承诺了 ${unhandled.join(" / ")} 快捷键，但 JS 里找不到对应处理`);
  else pass(`${promised.size} 个承诺的快捷键都有处理`);
}

/* ---------- 4. 视图白名单与真实 section 一致 ---------- */
console.log("\n=== 4. switchView 能到的视图是否都存在 ===");
const views = [...src.matchAll(/id="view-([\w-]+)"/g)].map(m => m[1]);
const switched = [...src.matchAll(/switchView\(\s*'([\w-]+)'\s*\)/g)].map(m => m[1]);
const badViews = [...new Set(switched)].filter(v => !views.includes(v));
if (badViews.length) badViews.forEach(v => fail(`switchView('${v}') 但没有 #view-${v}`));
else pass(`${new Set(switched).size} 个被切换的视图都有对应 section`);

/* ---------- 5. Tailwind 任意值：z-60 这种不存在的工具类 ---------- */
console.log("\n=== 5. 有没有用了不存在的 Tailwind 工具类 ===");
const zBad = [...src.matchAll(/class="[^"]*\bz-(\d+)\b[^"]*"/g)]
  .map(m => +m[1]).filter(n => ![0,10,20,30,40,50].includes(n));
if (zBad.length) fail(`用了 z-${[...new Set(zBad)].join("/")}，Tailwind 只有 z-0/10/20/30/40/50，这些会变成 z-index:auto（要写 z-[60]）`);
else pass("z-index 工具类都是合法的");

/* ---------- 6. 存储层是唯一出口 ---------- */
console.log("\n=== 6. localStorage 是否只在 Store 里被直接调用 ===");
const si = js.indexOf("const Store = (() => {");
const se = js.indexOf("function loadUserData()");
if (si < 0) fail("找不到 Store 层");
else {
  const outside = js.slice(0, si) + js.slice(se);
  const leaks = outside.match(/localStorage\.(?:set|get|remove)Item/g) || [];
  if (leaks.length) fail(`Store 之外还有 ${leaks.length} 处直接调用 localStorage`);
  else pass("所有存储读写都走 Store");
}

/* ---------- 7. Tailwind 透明度档位 ---------- */
console.log("\n=== 7. 有没有用了不存在的透明度档位 ===");
const OPACITY_STEPS = new Set([0,5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100]);
const badOp = [];
for (const m of src.matchAll(/class="[^"]*\b(?:bg|text|border)-[\w-]+\/(\d+)\b/g)) {
  const n = +m[1];
  if (!OPACITY_STEPS.has(n)) badOp.push(n);
}
if (badOp.length) fail(`用了 /${[...new Set(badOp)].join(" /")} 透明度，Tailwind 只有 5 的倍数档位，这些会变成完全透明（遮罩会失效）`);
else pass("透明度档位都是合法的");

console.log(`\n结果: ${ok} 通过 / ${bad} 失败`);
process.exit(bad ? 1 : 0);
