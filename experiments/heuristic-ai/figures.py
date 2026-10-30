"""用实验生成的数据画 SVG，并更新正文中的评测表。仅标准库。"""
from pathlib import Path
from html import escape
import json
import re
ROOT = Path(__file__).resolve().parents[2]
data = json.loads((ROOT/'public/demos/heuristic-ai/data.json').read_text())
DEST = ROOT/'public/images/posts/heuristic-ai-scoring'

def text(x,y,s,size=24,color='ink',anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" class="{color}" text-anchor="{anchor}">{escape(str(s))}</text>'

def line(x1,y1,x2,y2,color='muted',dash=''):
    return f'<path d="M{x1},{y1} L{x2},{y2}" style="fill:none" class="{color}" stroke="currentColor" stroke-width="3" stroke-dasharray="{dash}"/>'

def save(name,title,body,height):
    css='''svg{background:#f6f8fb;color:#172839;font-family:system-ui,"PingFang SC","Microsoft YaHei",sans-serif}.ink{fill:#172839;color:#172839}.muted{fill:#586878;color:#586878}.raw{fill:#9d4d05;color:#9d4d05}.exact{fill:#136b91;color:#136b91}.event{fill:#7950a0;color:#7950a0}@media(prefers-color-scheme:dark){svg{background:#17232f}.ink{fill:#edf3fa;color:#edf3fa}.muted{fill:#b3c2d1;color:#b3c2d1}.raw{fill:#ffc184;color:#ffc184}.exact{fill:#80d4f5;color:#80d4f5}.event{fill:#d5b4fc;color:#d5b4fc}}'''
    (DEST/name).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 {height}" role="img"><title>{escape(title)}</title><style>{css}</style>{body}</svg>\n')

row = next(r for r in data['probability'] if r['mode']=='independent' and r['hp']==1 and r['percent']==60)
b = text(28,40,'同一个一血靶，只剩一步',28)
b += '<circle cx="300" cy="126" r="42" fill="none" stroke="#7950a0" stroke-width="4"/>'
b += text(300,135,'1 HP',24,'event','middle')
b += line(100,202,265,151,'raw','6 5')+line(500,202,335,151,'exact')
b += text(30,240,'双发：各 60%',25,'raw')+text(350,240,'稳射：必中',25,'exact')
for y,label,key in [(298,'原始评分','raw'),(344,'实际期望','exact')]:
    b += text(30,y,f'{label}  {row[key]:g}',25,'raw' if key=='raw' else 'ink')
    b += text(350,y,f'{label}  {row["direct"]:g}',25,'exact')
b += text(28,405,'收益单位：实际扣血；两发独立，每发一伤',22,'muted')
save('choice.svg','双发评分 1.2，真实期望 0.84；稳射真实期望 1',b,435)
e=data['event']
b=text(28,40,'两个标签，同一次爆发',28)
b+=text(28,100,'形成组合  +2.4',25,'event')+text(330,100,'后续爆发  +2.4',25,'event')
b+=line(135,120,270,198,'event')+line(445,120,330,198,'event','7 5')
b+='<rect x="115" y="200" width="370" height="110" rx="12" fill="none" stroke="#7950a0" stroke-width="3"/>'
b+=text(300,243,e['id'],26,'event','middle')+text(300,282,'成功率 0.6 × 有效伤害 4',23,'ink','middle')
b+=text(28,365,f'标签相加：{e["raw"]}     事件结算一次：{e["exact"]}',25)
b+=text(28,410,'两个箭头是解释路径，不是两次伤害。',23,'muted')
save('event.svg','两个评分标签指向同一个 burst-once 事件',b,440)
b=text(28,40,'血量上限，改变的是结算',28)
b+=text(28,78,'两发独立，各以 p 命中；每发一伤',22,'muted')
for tick in (0,0.5,1,1.5,2):
    y=360-tick*110
    b+=line(90,y,550,y,'muted','2 7')+text(75,y+7,f'{tick:g}',20,'muted','end')
b+=text(28,116,'期望有效伤害',20,'muted')
for hp,color,dash in [(2,'raw','8 5'),(1,'exact','')]:
    rows=[r for r in data['probability'] if r['mode']=='independent' and r['hp']==hp]
    pts=' '.join(f'{90+r["percent"]*4.6},{360-r["exact"]*110}' for r in rows)
    b+=f'<polyline points="{pts}" style="fill:none" class="{color}" stroke="currentColor" stroke-width="4" stroke-dasharray="{dash}"/>'
for p in (0,0.5,1): b+=text(90+p*460,393,p,20,'muted','middle')
b+=text(550,425,'每发命中概率 p',22,'muted','end')
b+=text(28,470,'— 一血：1 − (1 − p)²',24,'exact')+text(28,507,'┄ 两血：2p（也等于原始评分）',24,'raw')
save('cap.svg','一血和两血目标下的实际期望伤害曲线',b,535)
b=text(28,40,'八血靶：同一个动作，不同的期限',27)
for y,turns in [(105,1),(285,2)]:
    s=next(s for s in data['states'] if s['hp']==8 and not s['armed'] and s['turns']==turns)
    b+=text(28,y,f'还剩 {turns} 步',25,'event')
    b+=text(28,y+49,'直射' + (' → 直射' if turns==2 else ' → 结束')+f'     总伤害 {s["q"]["direct"]}',25,'exact')
    b+=text(28,y+96,'蓄力' + (' → 爆发' if turns==2 else ' → 结束')+f'     总伤害 {s["q"]["charge"]}',25,'raw')
b+=text(28,455,'一步：2 对 0；两步：4 对 5。',24)
b+=text(28,495,'蓄力当步零伤；未使用的蓄力没有终局奖励。',21,'muted')
save('horizon.svg','剩一步选直射，剩两步选蓄力；奖励为累计有效伤害',b,525)

names={'fixed':'固定蓄力 3 分','immediate':'只看即时伤害','gated':'最后一步取消蓄力分'}
table='| 评分器 | 最优动作一致数 | 平均单步 regret | 平均整局损失 |\n| --- | ---: | ---: | ---: |\n'
for key,s in data['summary'].items():
    table+=f'| {names[key]} | {s["optimal_choices"]}/{s["states"]} | {s["mean_regret"]:g} | {s["mean_rollout_loss"]:g} |\n'
(ROOT/'experiments/heuristic-ai/summary.md').write_text(table)
post=ROOT/'src/content/posts/heuristic-ai-scoring.md'
if post.exists():
    source=post.read_text()
    source=re.sub(r'<!-- experiment-table:start -->.*?<!-- experiment-table:end -->',
        '<!-- experiment-table:start -->\n\n'+table+'\n<!-- experiment-table:end -->',source,flags=re.S)
    two = next(r for r in data['probability'] if r['mode']=='independent' and r['hp']==2 and r['percent']==60)
    probability_table = '| 第一发 | 第二发 | 概率 | 一血靶实际扣血 | 两血靶实际扣血 |\n| --- | --- | ---: | ---: | ---: |\n'
    for one, other in zip(row['outcomes'],two['outcomes']):
        hits = ['中' if h else '空' for h in one['hits']]
        probability_table += f'| {hits[0]} | {hits[1]} | {one["probability"]:g} | {one["damage"]} | {other["damage"]} |\n'
    source = re.sub(r'<!-- probability-table:start -->.*?<!-- probability-table:end -->',
        '<!-- probability-table:start -->\n\n'+probability_table+'\n<!-- probability-table:end -->',source,flags=re.S)
    post.write_text(source)
print('Generated 4 SVG figures and summary table.')
