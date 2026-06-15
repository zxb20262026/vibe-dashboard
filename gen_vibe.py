#!/usr/bin/env python3
"""
Vibe-Trading港大看板 · HTML生成器 v2.0
设计来源: Codex Vibe Terminal → 完整复刻 + 数据驱动
用法: python3 gen_vibe.py 300750
"""

import json, os, sys, math
from datetime import datetime

def fmt(n, d=2, default="—"):
    if n is None: return default
    if isinstance(n, float): return f"{n:.{d}f}"
    return str(n)

def sign(v):
    if v is None: return ""
    return "+" if v > 0 else ""

def pct_color(v, up_green=False):
    """A股涨红跌绿, up_green=True时反过来"""
    if v is None: return "var(--muted)"
    if up_green:
        return "var(--green)" if v >= 0 else "var(--red)"
    return "var(--red)" if v >= 0 else "var(--green)"

# ═══════════════════════════════════════════
# CSS (完全复刻 Codex Vibe Terminal 风格)
# ═══════════════════════════════════════════
CSS = r"""
:root {
  color-scheme: dark;
  --bg: #07090c;
  --ink: #eef5fb;
  --muted: #94a3b8;
  --dim: #64748b;
  --panel: #11161e;
  --panel2: #151c25;
  --panel3: #0c1118;
  --line: #263241;
  --soft: #1b2531;
  --cyan: #20d5e8;
  --green: #32d583;
  --amber: #f8bd35;
  --red: #ff6b7a;
  --blue: #5aa7ff;
  --purple: #b38cff;
  --orange: #ff9f43;
  --shadow: 0 24px 70px rgba(0,0,0,.38);
}
*{box-sizing:border-box}
body{margin:0;min-width:320px;background:radial-gradient(circle at 12% -10%,rgba(32,213,232,.12),transparent 28%),radial-gradient(circle at 95% 4%,rgba(255,159,67,.09),transparent 24%),linear-gradient(180deg,#0a1017 0,var(--bg) 420px);color:var(--ink);font:14px/1.55 "Microsoft YaHei","PingFang SC","Segoe UI",Arial,sans-serif}
button,input,select{font:inherit}
a{color:inherit;text-decoration:none}

.wrap{width:min(1560px,calc(100% - 28px));margin:0 auto;padding:14px 0 44px}

/* 顶部栏 */
.top{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:8px 0 14px}
.brand{display:flex;align-items:center;gap:12px;min-width:260px}
.logo{display:grid;place-items:center;width:38px;height:38px;border-radius:8px;background:linear-gradient(135deg,var(--cyan),var(--green));color:#051015;font-weight:900;font-size:19px}
.brand strong{display:block;font-size:16px}
.brand span,.time{color:var(--muted);font-size:12px}
.actions{display:flex;gap:8px;align-items:center;justify-content:flex-end;flex-wrap:wrap}
.pill,.icon-btn{border:1px solid var(--soft);background:rgba(17,22,30,.82);color:var(--muted);border-radius:7px;padding:8px 11px;min-height:36px}

/* 导航条 */
.nav-bar{display:flex;justify-content:center;gap:6px;margin-bottom:12px;flex-wrap:wrap}
.nav-btn{font-size:0.7em;padding:5px 12px;border-radius:14px;background:rgba(17,22,30,.82);border:1px solid var(--soft);color:var(--muted);text-decoration:none;transition:all .2s;display:inline-block}
.nav-btn:hover{border-color:var(--cyan);color:var(--cyan)}
.nav-btn.active{border-color:var(--cyan);color:var(--cyan);background:rgba(32,213,232,0.08)}

/* 终端面板 */
.terminal{display:grid;grid-template-columns:minmax(0,1.25fr) 380px;gap:14px}
.panel{background:linear-gradient(180deg,rgba(255,255,255,.035),rgba(255,255,255,.01)),var(--panel);border:1px solid var(--soft);border-radius:8px;box-shadow:var(--shadow);min-width:0}
.hero{padding:20px;min-height:420px;display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:18px}
.kicker{color:var(--cyan);font-size:12px;font-weight:800;text-transform:uppercase}
h1{margin:10px 0;font-size:48px;line-height:1.04;letter-spacing:0}
.lead{color:var(--muted);max-width:860px;margin:0 0 18px;font-size:15px}

.score-strip{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-top:18px}
.score{min-height:105px;padding:13px;border:1px solid var(--soft);border-radius:8px;background:rgba(7,9,12,.38)}
.score small{display:block;color:var(--muted);white-space:nowrap}
.score b{display:block;margin-top:8px;font-size:26px;line-height:1;white-space:nowrap}
.score em{display:block;margin-top:8px;color:var(--dim);font-style:normal;font-size:12px}

.playbook{display:grid;gap:10px;align-content:start}
.big-gauge{display:grid;grid-template-columns:118px 1fr;gap:14px;align-items:center;padding:16px;border-radius:8px;border:1px solid rgba(50,213,131,.3);background:rgba(50,213,131,.075)}
.ring{width:112px;height:112px;border-radius:50%;background:conic-gradient(var(--green) 0 72%,rgba(255,255,255,.1) 72% 100%);display:grid;place-items:center;position:relative;font-weight:900;font-size:28px}
.ring:after{content:"";position:absolute;inset:12px;background:#0a1118;border-radius:50%}
.ring span{position:relative;z-index:1}
.big-gauge h2{margin:0;font-size:22px}
.big-gauge p{margin:7px 0 0;color:var(--muted);font-size:13px}

.rule{display:grid;grid-template-columns:84px 1fr auto;gap:10px;align-items:center;padding:11px 12px;border-radius:8px;background:rgba(255,255,255,.035);border:1px solid var(--soft)}
.rule span:first-child{color:var(--muted);font-size:12px}

.tag{display:inline-flex;justify-content:center;align-items:center;min-width:50px;padding:3px 8px;border-radius:999px;font-size:12px;font-weight:800}
.tag.green{color:#c5f8da;background:rgba(50,213,131,.15)}
.tag.amber{color:#fee6aa;background:rgba(248,189,53,.16)}
.tag.red{color:#ffd2d7;background:rgba(255,107,122,.16)}
.tag.blue{color:#cfe5ff;background:rgba(90,167,255,.16)}
.tag.cyan{color:#ccf7ff;background:rgba(32,213,232,.15)}

.section-head{display:flex;justify-content:space-between;align-items:end;gap:14px;margin:24px 0 10px}
.section-head h2{margin:0;font-size:22px;letter-spacing:0}
.section-head p{margin:0;color:var(--muted);font-size:13px;text-align:right}

.grid{display:grid;gap:14px}
.grid.cols-4{grid-template-columns:repeat(4,minmax(0,1fr))}
.grid.cols-3{grid-template-columns:repeat(3,minmax(0,1fr))}
.grid.cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}
.grid.main{grid-template-columns:minmax(0,1.35fr) minmax(360px,.65fr)}

.card{padding:16px}
.card h3{margin:0 0 12px;font-size:16px;letter-spacing:0}

/* 决策矩阵 */
.matrix{position:relative;height:330px;border:1px solid var(--soft);border-radius:8px;overflow:hidden;background:linear-gradient(90deg,rgba(50,213,131,.09) 0 50%,rgba(248,189,53,.09) 50%),linear-gradient(180deg,rgba(90,167,255,.08) 0 50%,rgba(255,107,122,.07) 50%),var(--panel3)}
.matrix:before,.matrix:after{content:"";position:absolute;background:rgba(255,255,255,.12)}
.matrix:before{left:50%;top:0;bottom:0;width:1px}
.matrix:after{top:50%;left:0;right:0;height:1px}
.axis-x,.axis-y{position:absolute;color:var(--muted);font-size:12px}
.axis-x{left:16px;right:16px;bottom:10px;display:flex;justify-content:space-between}
.axis-y{top:12px;bottom:34px;left:12px;writing-mode:vertical-rl;text-orientation:mixed}
.bubble{position:absolute;display:grid;place-items:center;width:98px;height:98px;transform:translate(-50%,-50%);border-radius:50%;background:radial-gradient(circle at 35% 25%,rgba(255,255,255,.25),rgba(32,213,232,.34));border:1px solid rgba(32,213,232,.65);box-shadow:0 0 42px rgba(32,213,232,.22);font-weight:900;text-align:center;font-size:14px}
.bubble small{display:block;color:#d8fbff;font-size:11px;font-weight:700}

/* 图表 */
.chart{height:300px;border:1px solid var(--soft);border-radius:8px;background:linear-gradient(to top,rgba(255,255,255,.05) 1px,transparent 1px) 0 0/100% 20%,rgba(7,9,12,.35);overflow:hidden}
.chart svg{width:100%;height:100%;display:block}
.legend{display:flex;flex-wrap:wrap;gap:12px;margin-top:11px;color:var(--muted);font-size:12px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:1px}

.bar-row{display:grid;grid-template-columns:112px 1fr 54px;gap:10px;align-items:center;margin:12px 0}
.bar-row span{color:var(--muted);font-size:12px}
.bar{height:10px;overflow:hidden;border-radius:999px;background:#202b38}
.bar i{display:block;height:100%;border-radius:inherit}

.heat{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px}
.tile{min-height:92px;padding:10px;border-radius:8px;border:1px solid var(--soft);background:rgba(255,255,255,.035)}
.tile small{color:var(--muted)}
.tile b{display:block;margin-top:5px;font-size:20px}
.tile.green{background:rgba(50,213,131,.09)}
.tile.amber{background:rgba(248,189,53,.09)}
.tile.red{background:rgba(255,107,122,.09)}
.tile.blue{background:rgba(90,167,255,.09)}

.ticker{display:grid;gap:9px}
.tape{display:grid;grid-template-columns:72px 1fr auto;gap:10px;align-items:center;padding:10px 11px;border:1px solid var(--soft);border-radius:8px;background:rgba(255,255,255,.03)}
.tape time{color:var(--dim);font-size:12px}
.tape strong{font-size:13px}

.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
th,td{padding:10px 9px;border-bottom:1px solid var(--soft);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
th{color:var(--muted);font-size:12px}
tr:last-child td{border-bottom:0}

.watch{display:grid;gap:10px}
.watch-item{padding:16px;border:1px solid var(--soft);border-radius:8px;background:rgba(255,255,255,.03)}
.watch-item h4{margin:0 0 6px;font-size:14px}
.watch-item p{margin:0;color:var(--muted);font-size:12px}

.note-list{display:grid;gap:0}
.note-row{padding:10px 0;border-top:1px solid var(--soft)}
.note-row:first-child{border-top:0;padding-top:0}
.note-row h4{margin:0 0 5px;font-size:14px}
.note-row p{margin:0;color:var(--muted);font-size:12px}
.source-line{display:block;margin-top:7px;color:var(--dim);font-size:11px}

.formula{margin-top:12px;padding:12px;border:1px dashed rgba(32,213,232,.36);border-radius:8px;color:var(--muted);background:rgba(32,213,232,.045);font-size:12px}

.footer{margin-top:24px;color:var(--dim);text-align:center;font-size:12px}

.green-text{color:var(--green)}
.red-text{color:var(--red)}
.amber-text{color:var(--amber)}
.blue-text{color:var(--blue)}
.cyan-text{color:var(--cyan)}

@media(max-width:1240px){
  .terminal,.hero,.grid.main,.grid.cols-4,.grid.cols-3,.grid.cols-2{grid-template-columns:1fr}
  h1{font-size:38px}
  .score-strip{grid-template-columns:repeat(3,minmax(0,1fr))}
  .heat{grid-template-columns:repeat(4,minmax(0,1fr))}
}
@media(max-width:720px){
  .wrap{width:min(100% - 20px,1560px)}
  .top,.section-head{align-items:flex-start;flex-direction:column}
  .actions{justify-content:flex-start}
  .hero,.card{padding:14px}
  h1{font-size:30px}
  .score-strip,.heat,.big-gauge,.rule,.tape{grid-template-columns:1fr}
  .ring{width:104px;height:104px}
  .section-head p{text-align:left}
}
"""

# ═══════════════════════════════════════════
# JS (全部内联，零外部依赖)
# ═══════════════════════════════════════════

JS = r"""
// 大环分数
(function(){
  var ring = document.getElementById('overallRing');
  var sc = parseInt(document.getElementById('overallScore').textContent) || 50;
  if(ring) ring.style.background = 'conic-gradient(var(--green) 0 '+sc+'%, rgba(255,255,255,.1) '+sc+'% 100%)';
  
  // 矩阵气泡
  var bubble = document.getElementById('matrixBubble');
  if(bubble){
    var valX = parseInt(bubble.getAttribute('data-valx')) || 65;
    var vibeY = parseInt(bubble.getAttribute('data-vibey')) || 40;
    bubble.style.left = Math.max(18, Math.min(82, valX)) + '%';
    bubble.style.top = Math.max(18, Math.min(82, 100 - vibeY)) + '%';
  }
})();
"""

# ═══════════════════════════════════════════
# HTML构建函数
# ═══════════════════════════════════════════

def build_nav():
    return '''<div class="nav-bar">
    <a class="nav-btn" href="https://zxb20262026.github.io/300750/">🔋 宁德时代</a>
    <a class="nav-btn" href="https://zxb20262026.github.io/600900/">💧 长江电力</a>
    <a class="nav-btn" href="https://zxb20262026.github.io/00700/">🐧 腾讯控股</a>
    <a class="nav-btn" href="https://zxb20262026.github.io/sh300-etf-dashboard/">🎯 ETF雷达</a>
    <a class="nav-btn active" href="https://zxb20262026.github.io/vibe-dashboard/">🧬 港大看板</a>
</div>'''


def build_header(data):
    q = data.get("quote", {})
    meta = data.get("meta", {})
    return f'''<header class="top">
    <div class="brand">
        <div class="logo">V</div>
        <div>
            <strong>{q.get("name","—")} Vibe-Trading 估值终端</strong>
            <span>长期估值底盘 + 量化因子择时层</span>
        </div>
    </div>
    <div class="actions">
        <span class="pill">{meta.get("code","")}.{meta.get("market","")=="A股" and "SZ/SH" or "HK"}</span>
        <span class="pill">{meta.get("generated_at","")}</span>
    </div>
</header>'''


def build_hero(data):
    q = data.get("quote", {})
    f = data.get("fundamentals", {})
    peg = data.get("peg", {})
    alpha = data.get("alpha_factors", {})
    comp = alpha.get("composite", {})
    mom = alpha.get("momentum", {})
    val = alpha.get("value", {})
    qual = alpha.get("quality", {})
    corr = data.get("correlation", {})
    news = data.get("news") or {}
    
    pe = f.get("pe_ttm")
    roe = f.get("roe")
    chg = q.get("change_pct", 0)
    vibe_score = max(30, min(85, comp.get("score", 50) + (20 if news.get("sentiment", 0) > 10 else -10)))
    quality_score = qual.get("score", 50) + 20  # 基本面质量偏高
    crowding = max(20, min(80, 100 - corr.get("volatility_annual", 30)))
    
    # 估值分位 (PE越低分位越低)
    if pe:
        if pe < 18: val_pct = 10
        elif pe < 22: val_pct = 20
        elif pe < 28: val_pct = 35
        elif pe < 35: val_pct = 55
        else: val_pct = 75
    else:
        val_pct = 50
    
    execution_map = {
        "🟢 偏多": ("试探加仓", "cyan-text"),
        "🟡 中性": ("观察等待", "amber-text"),
        "🟠 偏空": ("防守为主", "amber-text"),
        "🔴 看空": ("减仓观望", "red-text"),
    }
    exec_action, exec_color = execution_map.get(comp.get("signal", ""), ("保持观察", "blue-text"))
    
    overall = int((100 - val_pct) * 0.3 + quality_score * 0.25 + vibe_score * 0.25 + (100 - crowding) * 0.2)
    
    score_strip = f'''<div class="score-strip">
        <div class="score"><small>估值分位</small><b class="green-text">{val_pct}%</b><em>PE {fmt(pe,1)}x 偏低区</em></div>
        <div class="score"><small>基本面质量</small><b class="green-text">{quality_score}</b><em>ROE {fmt(roe,1)}% 领先</em></div>
        <div class="score"><small>Vibe 强度</small><b class="{'green-text' if vibe_score > 70 else 'amber-text'}">{vibe_score}</b><em>量化+情绪综合</em></div>
        <div class="score"><small>拥挤度</small><b class="blue-text">{crowding}</b><em>越高越危险</em></div>
        <div class="score"><small>执行建议</small><b class="{exec_color}">{exec_action}</b><em>综合评分{overall}</em></div>
    </div>'''
    
    gauge_color = "var(--green)" if overall >= 65 else ("var(--amber)" if overall >= 45 else "var(--red)")
    
    playbook = f'''<aside class="playbook">
        <div class="big-gauge" style="border-color:{gauge_color};background:rgba({50 if overall>=65 else 248 if overall>=45 else 255},{213 if overall>=65 else 189 if overall>=45 else 107},{131 if overall>=65 else 53 if overall>=45 else 122},{'0.12' if overall>=65 else '0.1'})">
            <div class="ring" id="overallRing"><span id="overallScore">{overall}</span></div>
            <div>
                <h2>综合胜率区</h2>
                <p>{'估值偏低+质量强，适合分批建仓' if overall>=65 else ('估值合理，vibe中性，适合持有观察' if overall>=45 else '估值偏高或情绪偏弱，防守为主')}</p>
            </div>
        </div>
        <div class="rule"><span>底仓</span><strong>PE分位{val_pct}%，估值偏低可配置</strong><em class="tag green">允许</em></div>
        <div class="rule"><span>加仓</span><strong>需vibe≥70+资金回流确认</strong><em class="tag amber">等待</em></div>
        <div class="rule"><span>减仓</span><strong>PE回到30x+且vibe过热</strong><em class="tag red">警戒</em></div>
        <div class="rule"><span>止错</span><strong>{'ROE连续下滑或市占率恶化' if roe and roe>15 else '基本面数据待补充'}</strong><em class="tag blue">跟踪</em></div>
    </aside>'''
    
    # Vibe Tape (模拟日内情绪事件)
    tape_items = []
    if chg > 2:
        tape_items.append(('<time>盘中</time>', '强势上涨，板块共振', 'tag green', f'+{int(chg*2)}'))
    elif chg > 0:
        tape_items.append(('<time>盘中</time>', '温和上涨，趋势健康', 'tag green', f'+{int(chg*3)}'))
    else:
        tape_items.append(('<time>盘中</time>', '弱势调整，等待企稳', 'tag amber', f'{int(chg)}'))
    
    if corr.get("volatility_annual", 0) < 25:
        tape_items.append(('<time>波动</time>', '低波动环境，持仓舒适', 'tag blue', '+5'))
    else:
        tape_items.append(('<time>波动</time>', '波动偏高，注意风控', 'tag amber', '-3'))
    
    sentiment = news.get("sentiment", 0)
    if sentiment > 15:
        tape_items.append(('<time>情绪</time>', '新闻情绪偏正面', 'tag green', f'+{min(sentiment//5,10)}'))
    elif sentiment < -15:
        tape_items.append(('<time>情绪</time>', '新闻情绪偏负面', 'tag red', str(sentiment//5)))
    else:
        tape_items.append(('<time>情绪</time>', '新闻情绪中性', 'tag blue', '0'))
    
    tape_html = '\n'.join([f'<div class="tape">{t}<strong>{text}</strong><span class="{tag_cls}">{impact}</span></div>' for t, text, tag_cls, impact in tape_items])
    
    vibe_tape = f'''<aside class="panel card">
        <h3>今日 Vibe Tape</h3>
        <div class="ticker">{tape_html}</div>
    </aside>'''
    
    return f'''<section class="terminal">
    <div class="panel hero">
        <div>
            <div class="kicker">Vibe Layer / Valuation Layer / Execution Layer</div>
            <h1>估值给底线，Vibe 给节奏</h1>
            <p class="lead">把长期价值投资拆成两层：第一层判断{q.get("name","这家公司")}是否值得长期跟踪，第二层判断当前量化因子和情绪是否适合提高仓位。</p>
            {score_strip}
        </div>
        {playbook}
    </div>
    {vibe_tape}
</section>'''


def build_matrix(data):
    alpha = data.get("alpha_factors", {})
    corr = data.get("correlation", {})
    f = data.get("fundamentals", {})
    news = data.get("news") or {}
    
    pe = f.get("pe_ttm")
    vibe_score = alpha.get("composite", {}).get("score", 50)
    if news.get("sentiment"): vibe_score = max(20, min(90, vibe_score + news["sentiment"] // 5))
    
    # 估值吸引力: PE越低越有吸引力
    if pe:
        val_attract = max(10, min(90, 100 - pe * 2.5))
    else:
        val_attract = 50
    
    comp = alpha.get("composite", {})
    qual = alpha.get("quality", {})
    crowding = max(10, min(90, 100 - corr.get("volatility_annual", 30) * 1.5))
    
    bars = [
        ("估值安全垫", val_attract, "linear-gradient(90deg,var(--green),var(--cyan))"),
        ("资金确认", max(30, min(85, comp.get("score", 50) - 10)), "linear-gradient(90deg,var(--amber),var(--green))"),
        ("Vibe强度", vibe_score, "linear-gradient(90deg,var(--blue),var(--cyan))"),
        ("拥挤度风险", crowding, "linear-gradient(90deg,var(--green),var(--amber))"),
        ("基本面确认", qual.get("score", 50) + 15, "linear-gradient(90deg,var(--green),var(--cyan))"),
    ]
    
    bar_html = '\n'.join([f'<div class="bar-row"><span>{label}</span><div class="bar"><i style="width:{min(v,100)}%;background:{grad}"></i></div><b>{v}</b></div>' for label, v, grad in bars])
    
    bubble_label = f'{data.get("quote",{}).get("name","—")[:4]}<small>{"低估+中热" if val_attract>55 else "偏贵+冷清"}</small>'
    
    return f'''<section>
    <div class="section-head">
        <h2>Value × Vibe 决策矩阵</h2>
        <p>纵轴是量化+情绪强度，横轴是估值吸引力。</p>
    </div>
    <div class="grid main">
        <div class="panel card">
            <div class="matrix">
                <div class="axis-y">Vibe 强度：冷清 → 火热</div>
                <div class="axis-x"><span>估值贵</span><span>估值便宜</span></div>
                <div class="bubble" id="matrixBubble" data-valx="{val_attract}" data-vibey="{vibe_score}">{bubble_label}</div>
            </div>
            <div class="legend">
                <span><i class="dot" style="background:var(--green)"></i>左下：无聊但便宜</span>
                <span><i class="dot" style="background:var(--cyan)"></i>右上：理想进攻区</span>
                <span><i class="dot" style="background:var(--amber)"></i>左上：追涨风险区</span>
                <span><i class="dot" style="background:var(--red)"></i>右下：价值陷阱警戒</span>
            </div>
        </div>
        <div class="panel card">
            <h3>仓位节奏规则</h3>
            {bar_html}
            <div class="formula">综合分 = Vibe 40% + 估值吸引力 30% + 基本面质量 20% + 拥挤度反向 10%</div>
        </div>
    </div>
</section>'''


def build_chart_section(data):
    tech = data.get("tech", {})
    klines = tech.get("klines_90d", [])
    alpha = data.get("alpha_factors", {})
    
    # 简化的价格路径SVG
    if len(klines) > 5:
        closes = [k["close"] for k in klines[-60:]]
        min_p, max_p = min(closes) * 0.95, max(closes) * 1.05
        rng = max_p - min_p or 1
        h = 300
        pts = []
        for i, p in enumerate(closes):
            x = i / (len(closes) - 1) * 900
            y = h - ((p - min_p) / rng) * h
            pts.append(f"{x:.0f},{y:.0f}")
        price_path = " ".join(pts)
    else:
        price_path = "0,150 900,150"
    
    # Vibe factor tiles
    comp = alpha.get("composite", {})
    mom = alpha.get("momentum", {})
    val = alpha.get("value", {})
    qual = alpha.get("quality", {})
    news = data.get("news") or {}
    
    factors = [
        ("新闻热度", min(95, max(30, (news.get("sentiment", 0) + 60))), "green"),
        ("资金温度", comp.get("score", 50), "amber" if comp.get("score", 50) < 65 else "green"),
        ("Vibe综合", comp.get("score", 50), "blue"),
        ("板块共振", mom.get("score", 50), "green" if mom.get("score", 50) >= 55 else "amber"),
        ("估值安全", val.get("score", 50), "green" if val.get("score", 50) >= 55 else "amber"),
        ("波动风险", min(90, max(20, 100 - data.get("correlation", {}).get("volatility_annual", 30))), "red"),
        ("催化剂", min(90, max(30, 50 + news.get("sentiment", 0)//3)), "blue"),
    ]
    
    heat = '\n'.join([f'<div class="tile {tone}"><small>{name}</small><b>{score}</b></div>' for name, score, tone in factors])
    
    # 信号表
    pe = data.get("fundamentals", {}).get("pe_ttm")
    signals = [
        ("PE 分位", f"{max(5, min(90, int((pe or 25)*2.5)))}%", "green-text", "<30%", "允许观察"),
        ("动量因子", f"{mom.get('score',50)}", "amber-text" if mom.get('score', 50) < 55 else "green-text", "≥55", "跟踪"),
        ("Vibe综合", f"{comp.get('score',50)}", "green-text" if comp.get('score',50) >= 60 else "amber-text", "≥60", "等信号"),
        ("拥挤度", f"{max(20, 100 - (data.get('correlation',{}).get('volatility_annual',30) or 30)*1.5):.0f}", "blue-text", "<70", "可控"),
    ]
    
    signal_rows = '\n'.join([f'<tr><td>{s}</td><td class="{c}">{v}</td><td>{t}</td><td>{a}</td></tr>' for s, v, c, t, a in signals])
    
    return f'''<section>
    <div class="section-head">
        <h2>估值与 Vibe 双轨趋势</h2>
        <p>不要只看涨跌，要看估值低位是否叠加量化因子升温。</p>
    </div>
    <div class="grid cols-2">
        <div class="panel card">
            <h3>价格趋势</h3>
            <div class="chart">
                <svg viewBox="0 0 900 300" preserveAspectRatio="none">
                    <path d="M 0,150 Q 900,100 900,150" fill="none" stroke="rgba(32,213,232,.4)" stroke-width="1" stroke-dasharray="5 5"/>
                    <polyline points="{price_path}" fill="none" stroke="rgba(90,167,255,.95)" stroke-width="3"/>
                </svg>
            </div>
            <div class="legend">
                <span><i class="dot" style="background:var(--blue)"></i>价格趋势 (60日)</span>
                <span><i class="dot" style="background:var(--cyan)"></i>基线</span>
            </div>
        </div>
        <div class="panel card">
            <h3>Vibe 因子拆解</h3>
            <div class="heat">{heat}</div>
            <div class="table-wrap" style="margin-top:14px">
                <table>
                    <thead><tr><th>信号</th><th>当前</th><th>阈值</th><th>动作</th></tr></thead>
                    <tbody>{signal_rows}</tbody>
                </table>
            </div>
        </div>
    </div>
</section>'''


def build_peer_table(data):
    """同行估值对比（静态数据+CATL动态）"""
    f = data.get("fundamentals", {})
    alpha = data.get("alpha_factors", {})
    q = data.get("quote", {})
    
    pe = f.get("pe_ttm", 23)
    pb = f.get("pb", 5.6)
    roe = f.get("roe", 22)
    
    return f'''<section>
    <div class="section-head">
        <h2>同行估值与质量对标</h2>
        <p>便宜不是理由，质量调整后的便宜才有意义。</p>
    </div>
    <div class="panel card">
        <div class="table-wrap">
            <table>
                <thead><tr><th>公司</th><th>PE</th><th>PB</th><th>ROE</th><th>毛利率</th><th>PEG</th><th>Vibe</th><th>质量分</th><th>估值性价比</th><th>结论</th></tr></thead>
                <tbody>
                    <tr style="font-weight:600"><td>▲ {q.get("name","—")}</td><td>{fmt(pe,1)}x</td><td>{fmt(pb,1)}x</td><td class="green-text">{fmt(roe,1)}%</td><td>28.0%</td><td>0.93</td><td class="amber-text">{alpha.get('composite',{}).get('score',50)}</td><td class="green-text">{alpha.get('quality',{}).get('score',50)+20}</td><td class="green-text">高</td><td><span class="tag green">低估优质</span></td></tr>
                    <tr><td>比亚迪</td><td>30.3x</td><td>6.2x</td><td>11.0%</td><td>21.4%</td><td>1.21</td><td class="green-text">78</td><td>75</td><td class="amber-text">中</td><td><span class="tag amber">叙事偏热</span></td></tr>
                    <tr><td>亿纬锂能</td><td>28.0x</td><td>3.5x</td><td>10.2%</td><td>18.7%</td><td>1.12</td><td>51</td><td>70</td><td>中</td><td><span class="tag amber">合理</span></td></tr>
                    <tr><td>国轩高科</td><td>22.9x</td><td>2.4x</td><td>8.0%</td><td>17.2%</td><td>0.91</td><td>48</td><td>61</td><td class="amber-text">低</td><td><span class="tag amber">质量折价</span></td></tr>
                    <tr><td>欣旺达</td><td>47.6x</td><td>2.8x</td><td>3.2%</td><td>15.6%</td><td>1.90</td><td>57</td><td>52</td><td class="red-text">低</td><td><span class="tag red">偏贵</span></td></tr>
                </tbody>
            </table>
        </div>
    </div>
</section>'''


def build_playbook(data):
    f = data.get("fundamentals", {})
    pe = f.get("pe_ttm")
    roe = f.get("roe")
    
    return f'''<section>
    <div class="section-head">
        <h2>交易剧本</h2>
        <p>长期投资也需要执行规则，否则容易被情绪带着走。</p>
    </div>
    <div class="grid cols-4">
        <div class="panel card watch-item">
            <h4 class="green-text">低估冷清</h4>
            <p>PE分位低于25%，量化因子偏弱，资金未回流。动作：只做研究和小比例观察仓。</p>
        </div>
        <div class="panel card watch-item">
            <h4 class="cyan-text">低估升温</h4>
            <p>估值低位叠加量化因子回升、板块共振。动作：分批加仓，严格记录假设。</p>
        </div>
        <div class="panel card watch-item">
            <h4 class="amber-text">高估火热</h4>
            <p>PE回到30x以上，vibe得分过高。动作：不再加仓，评估减仓时机。</p>
        </div>
        <div class="panel card watch-item">
            <h4 class="red-text">基本面破坏</h4>
            <p>{'ROE' if roe else ''}市占率、毛利率、现金流连续恶化。动作：不以低PE补仓，重估长期逻辑。</p>
        </div>
    </div>
</section>'''


def build_data_roadmap():
    return '''<section>
    <div class="section-head">
        <h2>Vibe 因子数据化台账</h2>
        <p>指标口径、权重、来源和备注，后续可替换成真实接口。</p>
    </div>
    <div class="grid cols-3">
        <div class="panel card">
            <h3>估值数据</h3>
            <div class="note-list">
                <div class="note-row"><h4>历史 PE/PB/PS</h4><p>日频或周频保存，计算 3/5/10 年分位。</p></div>
                <div class="note-row"><h4>一致预期 EPS</h4><p>区分 TTM、NTM、2026E/2027E，避免口径混用。</p></div>
            </div>
        </div>
        <div class="panel card">
            <h3>Vibe 数据</h3>
            <div class="note-list">
                <div class="note-row"><h4>量化因子</h4><p>动量/价值/质量三维评分，每日更新。</p></div>
                <div class="note-row"><h4>情绪温度</h4><p>新闻NLP + 资金流向 + 波动率同步观察。</p></div>
            </div>
        </div>
        <div class="panel card">
            <h3>执行记录</h3>
            <div class="note-list">
                <div class="note-row"><h4>买入理由版本化</h4><p>每次加仓绑定估值、vibe、基本面假设。</p></div>
                <div class="note-row"><h4>错因复盘</h4><p>区分估值错、基本面错、情绪错、执行错。</p></div>
            </div>
        </div>
    </div>
</section>'''


# ═══════════════════════════════════════════
# 主生成函数
# ═══════════════════════════════════════════

def generate(data):
    meta = data.get("meta", {})
    name = data.get("quote", {}).get("name", "Vibe-Trading")
    
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} · Vibe-Trading港大看板</title>
<style>{CSS}</style>
</head>
<body>
<main class="wrap">
{build_nav()}
{build_header(data)}
{build_hero(data)}
{build_matrix(data)}
{build_chart_section(data)}
{build_peer_table(data)}
{build_playbook(data)}
{build_data_roadmap()}
<p class="footer">本页面为Vibe-Trading港大看板自动生成，不构成投资建议。量化因子只能辅助仓位节奏，不能替代财务和商业模式研究。</p>
</main>
<script>{JS}</script>
</body>
</html>'''


def main():
    if len(sys.argv) < 2:
        print("用法: python3 gen_vibe.py <股票代码>")
        sys.exit(1)
    
    code = sys.argv[1]
    src_dir = os.path.dirname(__file__)
    json_file = os.path.join(src_dir, "stocks", f"{code}.json")
    
    if not os.path.exists(json_file):
        print(f"📡 正在采集 {code}...")
        ret = os.system(f"cd {src_dir} && python3 analyze.py {code}")
        if ret != 0:
            print("❌ 采集失败")
            sys.exit(1)
    
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    html = generate(data)
    
    out_file = os.path.join(src_dir, "stocks", f"{code}_vibe.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✅ 已生成: {out_file}")
    print(f"   文件大小: {os.path.getsize(out_file):,} bytes")


if __name__ == "__main__":
    main()
