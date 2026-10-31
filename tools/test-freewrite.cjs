#!/usr/bin/env node
/* 随手记分类器测试：从 index.html 提取 freewriteClassify 纯函数。
 * 覆盖：用户备忘录样例内容（语法规则/单词+中文/句型）与杂记兜底。 */
const fs = require("fs");
const path = require("path");

const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const m = html.match(/function freewriteClassify\([\s\S]*?\n    \}/);
if (!m) { console.error("✗ 没找到 freewriteClassify"); process.exit(1); }
const freewriteClassify = new Function(m[0] + "; return freewriteClassify;")();

let pass = 0, fail = 0;
const ok = (name, cond) => {
  if (cond) { pass++; console.log("  ok  ", name); }
  else { fail++; console.log("  FAIL", name, JSON.stringify(cond)); }
};
const has = (tags, t) => tags.includes(t);

console.log("=== 用户备忘录样例 ===");
ok("Grammar语法规则→语法", has(freewriteClassify(
  'Granted is not of course in the sense of naturally. It marks a concession: the writer admits a point'), "语法"));
ok("单词+中文释义→词汇", has(freewriteClassify("Doomed to 注定\nbe doomed to failure 注定失败"), "词汇"));
ok("Venerate 高受人尊敬的→词汇", has(freewriteClassify("Venerate\nHighly regarded 受人尊敬的"), "词汇"));
ok("Straddle句型搭配→句型", has(freewriteClassify("Straddle the line between 跨越了界限\nstraddle two genres 融合两种风格"), "句型"));
ok("orthodox+中文→词汇", has(freewriteClassify("orthodox 正统\nUnequivocal 非正统"), "词汇"));

console.log("=== 其他类别 ===");
ok("slope/方程→数学", has(freewriteClassify("slope of the line, 方程的解"), "数学"));
ok("主旨/推断→阅读", has(freewriteClassify("main idea 和 inference 的区别"), "阅读"));
ok("无特征→杂记兜底", has(freewriteClassify("明天带水杯"), "杂记"));
ok("空文本→杂记", Array.isArray(freewriteClassify("")) && freewriteClassify("").length === 1);

console.log(`\n${pass} 通过 / ${fail} 失败`);
process.exit(fail ? 1 : 0);
