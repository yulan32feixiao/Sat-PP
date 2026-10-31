#!/usr/bin/env node
/* mathify 单元测试：从 index.html 提取数学排版引擎，验证转换结果。
 * 覆盖：分数堆叠 / 根号 / 指数 / 千分位 / 运算符 / 散文负例（不能误伤英文）。 */
const fs = require("fs");
const path = require("path");

const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const m = html.match(/\/\* =+ 数学规范排版[\s\S]*?(?=\n\s*\/\* =+ 计算器)/);
if (!m) { console.error("✗ 没找到 mathify 代码块"); process.exit(1); }

// mathify 三个纯函数不依赖 DOM，直接在 Node 沙箱里跑
const code = m[0]
  .replace(/^[\s\S]*?const MATH_FUNCS/, "const MATH_FUNCS")
  .replace(/\n\s*function mathRender[\s\S]*$/, "\n");
let mathifyHTML;
try {
  mathifyHTML = new Function(code + "; return mathifyHTML;")();
} catch (e) { console.error("✗ 提取失败:", e.message); process.exit(1); }
if (typeof mathifyHTML !== "function") { console.error("✗ 提取失败"); process.exit(1); }

let pass = 0, fail = 0;
function t(name, src, must, mustNot) {
  const out = mathifyHTML(src);
  // data-tex 是 URI 编码的，断言前解出来一起查
  const texes = (out.match(/data-tex="([^"]*)"/g) || [])
    .map(s => decodeURIComponent(s.slice(9, -1)));
  const probe = out + " ||| " + texes.join(" | ");
  const okM = (!must || must.every(x => probe.includes(x)));
  const okN = (!mustNot || mustNot.every(x => !probe.includes(x)));
  if (okM && okN) { pass++; console.log("  ok  ", name); }
  else { fail++; console.log("  FAIL", name, "\n       got:", probe); }
}

console.log("=== 分数（线性 → \\frac 堆叠）===");
t("系数分数 3/2x", "What is the slope of 3/2x+15 in the xy-plane?",
  ["\\frac{3}{2}"], []);
t("负分数 −1/7y", "3/2x−1/7y=29", ["\\frac{3}{2}", "\\frac{1}{7}"], []);
t("括号整体分子 4(cx+4)/2", "4(cx+4)/2=6x−4", ["\\frac{4(cx+4)}{2}"], []);
t("指数括号底 2,100(a)^x", "y=2,100(a)<sup>x</sup>", ["2{,}100", "(a)^{x}"], []);
t("字母分数 p/1,000", "What is the value of p/1,000 ?", ["\\frac{p}{1{,}000}"], []);

console.log("=== 指数（<sup> → ^{}）===");
t("x^2", "the graph of y=x<sup>2</sup>−169", ["y=x^{2}-169"], ["<sup>"]);
t("平方差 n^2", "n<sup>2</sup>+3n−340=0", ["n^{2}+3n-340=0"], []);
t("嵌套括号指数", "(x+n)(x+11)=x<sup>2</sup>+(n+11)x+11n", ["x^{2}+(n+11)x+11n"], []);

console.log("=== 根号 / π / 运算符 ===");
t("√9", "What is √9 ?", ["\\sqrt{9}"], []);
t("√(x+2)", "if √(x+2)=5", ["\\sqrt{x+2}"], []);
t("π", "the area is 3π", ["3\\pi"], []);
t("乘号", "2×60=120", ["2\\times 60=120"], []);
t("小于等于", "if x≤10", ["x\\leq 10"], []);

console.log("=== 散文负例（不能误伤）===");
t("x-intercept 不转", "What is an x -intercept of the graph?",
  [], ["ktx"]);
t("纯年份不转", "In 1879, botanist William Beal buried 20 bottles.",
  [], ["ktx"]);
t("普通单词不转", "The Museum of Modern Art exhibits games.",
  [], ["ktx"]);
t("f(x) 无数字不转", "The function f(x) gives the area.", [], ["ktx"]);
t("已有KaTeX不重复", '<span class="ktx" data-tex="x"></span>keep',
  ['class="ktx"', "keep"], []);
t("官方MathML跳过", "see <math><mi>x</mi></math> here", ["<math>"], ["ktx"]);

console.log("=== HTML结构保护 ===");
t("标签内属性不动", '<img src="fig2026/a.png" alt="figure"> and 3/4',
  ["src=\"fig2026/a.png\"", "\\frac{3}{4}"], []);
t("段落标签保留", "<p>y=x<sup>2</sup></p>", ["<p>", "</p>", "x^{2}"], []);

console.log(`\n${pass} 通过 / ${fail} 失败`);
process.exit(fail ? 1 : 0);
