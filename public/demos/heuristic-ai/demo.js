const $ = (id) => document.getElementById(id);
const fmt = (n) => Number(n.toFixed(4)).toString();
const pick = (score, direct) =>
	score > direct ? "双发" : score < direct ? "稳射" : "并列";
const labels = { direct: "直射", charge: "蓄力", burst: "爆发" };
$("theme").addEventListener("click", () => {
	const root = document.documentElement;
	const dark = root.dataset.theme
		? root.dataset.theme === "dark"
		: matchMedia("(prefers-color-scheme: dark)").matches;
	root.dataset.theme = dark ? "light" : "dark";
});
try {
	const response = await fetch("./data.json");
	if (!response.ok) throw new Error(`HTTP ${response.status}`);
	const data = await response.json();
	const rows = new Map(
		data.probability.map((r) => [`${r.mode}/${r.hp}/${r.percent}`, r]),
	);
	function render() {
		const mode = $("mode").value;
		const max = mode === "exclusive" ? 50 : 100;
		$("probability").max = max;
		$("probability").value = Math.min(Number($("probability").value), max);
		const percent = Number($("probability").value);
		const hp = Number($("hp").value);
		$("p-label").textContent = `${percent}%`;
		$("mode-note").textContent =
			mode === "exclusive"
				? "互斥模式要求 2p ≤ 1；切换时会把概率限制到 50% 以内。"
				: mode === "shared"
					? "同一次判定控制两发：两发同时命中，或同时落空。"
					: "两发分别判定；联合概率可以相乘。";
		const r = rows.get(`${mode}/${hp}/${percent}`);
		$("meters").replaceChildren();
		for (const [key, label, cls] of [
			["raw", "原始：命中数期望", "raw"],
			["cap_mean", "先期望再封顶", "cap"],
			["exact", "逐结果结算的期望", "exact"],
			["direct", "稳射的实际收益", "direct"],
		]) {
			const row = document.createElement("div");
			row.className = `meter ${cls}`;
			const title = document.createElement("span");
			title.textContent = label;
			const track = document.createElement("div");
			track.className = "track";
			track.setAttribute("aria-hidden", "true");
			const fill = document.createElement("div");
			fill.className = "fill";
			fill.style.width = `${r[key] * 50}%`;
			track.append(fill);
			const value = document.createElement("span");
			value.className = "value";
			value.textContent = fmt(r[key]);
			row.append(title, track, value);
			$("meters").append(row);
		}
		$("decision").textContent =
			hp === 0
				? "目标已清空，没有合法射击动作。原始计分若仍给出正数，说明遗漏了终止条件。"
				: `原始评分：${pick(r.raw, r.direct)}；先期望再封顶：${pick(r.cap_mean, r.direct)}；按实际收益：${pick(r.exact, r.direct)}。`;
		$("outcomes").replaceChildren();
		for (const outcome of r.outcomes) {
			const tr = document.createElement("tr");
			for (const value of [
				outcome.hits.map((h) => (h ? "命中" : "落空")).join(" / "),
				fmt(outcome.probability),
				outcome.damage,
			]) {
				const td = document.createElement("td");
				td.textContent = value;
				tr.append(td);
			}
			$("outcomes").append(tr);
		}
		$("fraction").textContent =
			`逐行以概率乘实际扣血，再相加：${r.exact_fraction} = ${fmt(r.exact)}。`;
		const state = data.states.find(
			(s) =>
				s.hp === 8 && !s.armed && s.turns === Number($("turns").value),
		);
		const optimum = Math.max(...Object.values(state.q));
		const best = Object.keys(state.q)
			.filter((a) => state.q[a] === optimum)
			.map((a) => labels[a])
			.join("、");
		$("horizon").textContent =
			`先直射，后续最优：${state.q.direct}；先蓄力，后续最优：${state.q.charge}。最优开局：${best}。固定评分始终给直射 2 分、蓄力 3 分。若全程使用固定评分器，实际总伤害为 ${state.policies.fixed.return_}；最后一步取消蓄力分后为 ${state.policies.gated.return_}。`;
	}
	$("controls").querySelector("fieldset").disabled = false;
	$("status").textContent = "";
	for (const id of ["hp", "mode", "probability", "turns"])
		$(id).addEventListener("input", render);
	render();
} catch (error) {
	$("status").textContent =
		"结果表未能加载。请刷新页面，或返回文章查看静态推导。";
	console.error(error);
}
