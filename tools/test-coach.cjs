#!/usr/bin/env node
/* AI教练核心引擎测试：从 index.html 提取 COACH-CORE 纯函数块独立运行。
 * 覆盖：数据聚合（正确率/错因/复发/四象限/到期）与今日任务规则（数量边界/弱点挑选/空状态）。 */
const fs = require("fs");
const path = require("path");

const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const m = html.match(/\/\* ===== COACH-CORE START =====[\s\S]*?===== COACH-CORE END ===== \*\//);
if (!m) { console.error("✗ 没找到 COACH-CORE 代码块"); process.exit(1); }
const { coachAggregate, coachTodayPlan } = new Function(
  m[0] + "; return { coachAggregate, coachTodayPlan };")();

let pass = 0, fail = 0;
const ok = (name, cond) => {
  if (cond) { pass++; console.log("  ok  ", name); }
  else { fail++; console.log("  FAIL", name); }
};

const NOW = 1700000000000;
const DAY = 86400000;

// ---------- coachAggregate ----------
console.log("=== coachAggregate 数据聚合 ===");
const attempts = [
  { qid: "q1", cat: "grammar", sk: "Transitions", sec: 1, ok: true,  ms: 40000, tag: "", ts: NOW - DAY, },
  { qid: "q2", cat: "grammar", sk: "Transitions", sec: 1, ok: false, ms: 80000, tag: "逻辑连接词", ts: NOW - DAY },
  { qid: "q3", cat: "grammar", sk: "Transitions", sec: 1, ok: false, ms: 90000, tag: "逻辑连接词", ts: NOW - 8 * DAY }, // 7天外
  { qid: "q4", cat: "vocab", sk: "Words in Context", sec: 1, ok: true, ms: 60000, tag: "", ts: NOW - 2 * DAY },
];
const mistakes = {
  q2: { qid: "q2", mastered: false, due: NOW - DAY, lapses: 1 },
  q3: { qid: "q3", mastered: false, due: NOW + DAY, lapses: 2 },  // 未到期
  q9: { qid: "q9", mastered: true,  due: NOW - DAY, lapses: 3 },  // 已掌握不算
};
const agg = coachAggregate(attempts, mistakes, NOW);

ok("总作答=4 总对=2", agg.totals.n === 4 && agg.totals.ok === 2);
ok("总正确率=50%", agg.totals.acc === 50);
ok("到期错题只算未掌握且到期=1", agg.dueCount === 1);
const tr = agg.skills.find(s => s.sk === "Transitions");
ok("Transitions 3题1对 acc=33%", tr && tr.n === 3 && tr.ok === 1 && tr.acc === 33);
ok("错因tag计数：逻辑连接词×2", tr && tr.tags["逻辑连接词"] === 2);
ok("复发lapses=2（取错题表最大值）", tr && tr.lapses === 2);
ok("近7天只计3题（q3在7天外）", tr && tr.recent7.n === 2);
ok("弱点排序：Transitions(33%)排在Words(100%)前",
   agg.skills[0].sk === "Transitions" && agg.skills[1].sk === "Words in Context");
const quadrants = agg.quad;
ok("四象限计数：快对2 慢错2",
   quadrants.slowRight === 0 && quadrants.slowWrong === 2 && quadrants.fastRight === 2 && quadrants.fastWrong === 0);
const empty = coachAggregate([], {}, NOW);
ok("空数据：0题0%，skills为空数组，不抛错", empty.totals.n === 0 && empty.skills.length === 0);

// ---------- coachTodayPlan ----------
console.log("=== coachTodayPlan 今日任务规则 ===");
const aggWeak = {
  totals: { n: 20, ok: 10, acc: 50 }, dueCount: 18,
  skills: [
    { cat: "grammar", sk: "Transitions", n: 10, ok: 3, acc: 30, avgMs: 60000, tags: {}, lapses: 2, recent7: { n: 0, ok: 0 } },
    { cat: "vocab", sk: "Words in Context", n: 8, ok: 5, acc: 63, avgMs: 50000, tags: {}, lapses: 0, recent7: { n: 0, ok: 0 } },
    { cat: "reading", sk: "Inference", n: 30, ok: 27, acc: 90, avgMs: 60000, tags: {}, lapses: 0, recent7: { n: 0, ok: 0 } },
  ], quad: {}, generatedAt: NOW,
};
const plan = coachTodayPlan(aggWeak, { dailyMinutes: 40 }, NOW);
ok("第一个任务=到期错题重练，n=min(18,15)=15",
   plan.tasks[0].key === "due" && plan.tasks[0].n === 15);
ok("到期任务的why含到期数", plan.tasks[0].why.includes("18"));
ok("弱点任务挑最弱两个考点（30%/63%），90%的不挑",
   plan.tasks[1].sk === "Transitions" && plan.tasks[2].sk === "Words in Context");
ok("弱点任务n在8~20之间", plan.tasks.slice(1).every(t => t.n >= 8 && t.n <= 20));
ok("每个任务都带why（透明规则）", plan.tasks.every(t => t.why && t.why.length > 5));
ok("预计时长不超过每日时长太多（≤55分钟）", plan.estMinutes <= 55);

const planNoWeak = coachTodayPlan({
  totals: { n: 5, ok: 5, acc: 100 }, dueCount: 0,
  skills: [{ cat: "math", sk: "Algebra", n: 5, ok: 5, acc: 100, avgMs: 60000, tags: {}, lapses: 0, recent7: { n: 0, ok: 0 } }],
  quad: {}, generatedAt: NOW,
}, {}, NOW);
ok("无弱点无到期→保持手感任务10题", planNoWeak.tasks.length === 1 &&
   planNoWeak.tasks[0].key === "maintain" && planNoWeak.tasks[0].n === 10);

const planLowN = coachTodayPlan({
  totals: { n: 3, ok: 0, acc: 0 }, dueCount: 0,
  skills: [{ cat: "grammar", sk: "Transitions", n: 3, ok: 0, acc: 0, avgMs: 0, tags: {}, lapses: 0, recent7: { n: 0, ok: 0 } }],
  quad: {}, generatedAt: NOW,
}, {}, NOW);
ok("题数<5的考点不算弱点（样本不足）→保持手感", planLowN.tasks[0].key === "maintain");

const planLong = coachTodayPlan(aggWeak, { dailyMinutes: 300 }, NOW);
ok("每日时长钳制在≤180分钟", planLong.dailyMinutes === 180);
const planShort = coachTodayPlan(aggWeak, { dailyMinutes: 5 }, NOW);
ok("每日时长钳制在≥10分钟", planShort.dailyMinutes === 10);

console.log(`\n${pass} 通过 / ${fail} 失败`);
process.exit(fail ? 1 : 0);
