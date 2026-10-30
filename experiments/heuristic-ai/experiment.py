"""原创靶场：标准库精确枚举。规则和评测范围见 README.md。"""
from fractions import Fraction as F
from functools import lru_cache
from itertools import product
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'public/demos/heuristic-ai/data.json'


def outcomes(p, mode):
    """两发的联合分布；p 是各发的边缘命中概率。"""
    if mode == 'independent':
        return [((p if a else 1-p)*(p if b else 1-p), (a,b))
                for a,b in product((0,1), repeat=2)]
    if mode == 'shared':
        return [(1-p,(0,0)), (p,(1,1))]
    if mode == 'exclusive' and 0 <= p <= F(1,2):
        return [(1-2*p,(0,0)), (p,(1,0)), (p,(0,1))]
    raise ValueError((p, mode))


def expected_damage(rows, hp):
    assert hp >= 0 and sum(p for p,_ in rows) == 1
    assert all(p >= 0 for p,_ in rows)
    return sum(p*min(hp, sum(hits)) for p,hits in rows)


def actions(armed):
    return ('direct', 'burst') if armed else ('direct', 'charge')


def step(hp, armed, action):
    """直射保留蓄力，爆发消耗蓄力；每次调用消耗一步。"""
    assert hp > 0 and action in actions(armed)
    nominal = {'direct':2, 'charge':0, 'burst':5}[action]
    reward = min(hp, nominal)
    ready = True if action == 'charge' else False if action == 'burst' else armed
    return reward, hp-reward, ready


@lru_cache(None)
def value(hp, armed, turns):
    if hp == 0 or turns == 0:
        return 0
    return max(q_values(hp, armed, turns).values())


def q_values(hp, armed, turns):
    result = {}
    for a in actions(armed):
        r, next_hp, ready = step(hp, armed, a)
        result[a] = r + value(next_hp, ready, turns-1)
    return result


def enumerate_sequences(hp, armed, turns):
    """前向展开合法序列，不调用 value 或启发式评分；共享公开转移。"""
    frontier = [(hp,armed,0)]
    for _ in range(turns):
        following = []
        for remaining,ready,total in frontier:
            if remaining == 0:
                following.append((remaining,ready,total))
            else:
                for a in actions(ready):
                    r,h,b = step(remaining,ready,a)
                    following.append((h,b,total+r))
        frontier = following
    return max(total for _,_,total in frontier)


def scores(hp, armed, turns, policy):
    result = {}
    for a in actions(armed):
        immediate = step(hp,armed,a)[0]
        bonus = 3 if a == 'charge' else 0
        if policy == 'immediate' or (policy == 'gated' and turns == 1):
            bonus = 0
        result[a] = {'immediate':immediate, 'future_bonus':bonus, 'total':immediate+bonus}
    return result


def choose(scores_by_action):
    # 同分按合法动作顺序，直射优先；所有评分器采用相同约定。
    return max(scores_by_action, key=lambda a:scores_by_action[a]['total'])


def rollout(hp,armed,turns,policy):
    total = 0
    while hp and turns:
        a = choose(scores(hp,armed,turns,policy))
        r,hp,armed = step(hp,armed,a)
        total += r
        turns -= 1
    return total


def main():
    assert expected_damage(outcomes(F(3,5),'independent'),1) == F(21,25)
    assert expected_damage(outcomes(F(3,5),'shared'),1) == F(3,5)
    assert expected_damage(outcomes(F(1,2),'exclusive'),1) == 1
    probability_rows = []
    for mode in ('independent','shared','exclusive'):
        for hp in range(5):
            for percent in range(51 if mode == 'exclusive' else 101):
                p = F(percent,100)
                rows = outcomes(p,mode)
                exact = expected_damage(rows,hp)
                naive = 2*p
                union = sum(prob for prob,hits in rows if any(hits)) if hp else F(0)
                probability_rows.append(dict(mode=mode,hp=hp,percent=percent,
                    raw=float(naive),cap_mean=float(min(hp,naive)),dedup=float(union),
                    exact=float(exact),exact_fraction=str(exact),direct=min(hp,1),
                    outcomes=[dict(probability=float(prob),hits=list(hits),damage=min(hp,sum(hits)))
                              for prob,hits in rows]))
                assert 0 <= exact <= hp
                if hp == 0: assert exact == 0
                if hp >= 2: assert exact == 2*p  # 线性期望不要求独立。
                if hp == 1 and mode == 'independent': assert exact == 1-(1-p)**2
    policies = ('fixed','immediate','gated')
    states = []
    for hp,armed,turns in product(range(1,11),(False,True),range(1,5)):
        q = q_values(hp,armed,turns)
        optimum = value(hp,armed,turns)
        assert optimum == enumerate_sequences(hp,armed,turns)
        entries = {}
        for policy in policies:
            breakdown = scores(hp,armed,turns,policy)
            choice = choose(breakdown)
            entries[policy] = dict(scores=breakdown,choice=choice,
                ranking=sorted(breakdown,key=lambda a:breakdown[a]['total'],reverse=True),
                regret=optimum-q[choice],return_=rollout(hp,armed,turns,policy))
        states.append(dict(hp=hp,armed=armed,turns=turns,q=q,optimal=optimum,policies=entries))
    for hp,armed,turns in product(range(11),(False,True),range(5)):
        assert value(hp,armed,turns) == enumerate_sequences(hp,armed,turns)
    summary = {}
    for policy in policies:
        entries = [s['policies'][policy] for s in states]
        summary[policy] = dict(states=len(states),optimal_choices=sum(e['regret']==0 for e in entries),
            mean_regret=sum(e['regret'] for e in entries)/len(states),
            max_regret=max(e['regret'] for e in entries),
            mean_rollout_loss=sum(s['optimal']-s['policies'][policy]['return_'] for s in states)/len(states))
    event = {'id':'burst-once','probability':0.6,'damage':4,'labels':['形成组合','后续爆发'],
             'raw':float(2*F(3,5)*4),'exact':float(F(3,5)*4),'alternative':3}
    assert event['raw'] == 4.8 and event['exact'] == 2.4
    assert q_values(8,False,1) == {'direct':2,'charge':0}
    assert q_values(8,False,2) == {'direct':4,'charge':5}
    assert [a for a in sorted({'a':4,'b':3},key={'a':4,'b':3}.get)] == ['b','a']
    assert sorted({'a':2,'b':1},key={'a':2,'b':1}.get) == ['b','a']
    result = dict(rules_version=1,probability=probability_rows,event=event,states=states,summary=summary,
                  verification=dict(probability_rows=len(probability_rows),sequence_states=110))
    # 每个状态一行，保留完整明细，同时让生成文件的差异可定位。
    blocks = []
    for key, val in result.items():
        encoded = ('[\n' + ',\n'.join('    '+json.dumps(row,ensure_ascii=False) for row in val) + '\n  ]'
                   if isinstance(val,list) else json.dumps(val,ensure_ascii=False))
        blocks.append('  '+json.dumps(key)+': '+encoded)
    OUT.write_text('{\n'+',\n'.join(blocks)+'\n}\n')
    print(json.dumps({'summary':summary,'verification':result['verification']},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
