#!/usr/bin/env python3
"""
Vibe-Trading 统一看板 · HTML生成器 v1.0
从 stocks/<code>.json 读取数据 → 生成完整7Tab分析页面
用法: python3 gen_unified.py 300750
"""

import json, os, sys, math
from datetime import datetime

def fmt(n, d=2, default="—"):
    if n is None: return default
    return f"{n:.{d}f}"

def color_pct(v, up_red=True):
    if v is None: return "#8b949e"
    if up_red:
        return "#f85149" if v >= 0 else "#3fb950"
    return "#3fb950" if v >= 0 else "#f85149"

def sign(v):
    if v is None: return ""
    return "+" if v > 0 else ""

# ═══════════════════════════════════════════
# CSS (暗色主题 + Tab切换 + 响应式)
# ═══════════════════════════════════════════
CSS = r"""*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Microsoft YaHei","PingFang SC",sans-serif;background:#0a0e17;color:#e6edf3;line-height:1.5;padding:16px;min-height:100vh}
.wrap{max-width:1000px;margin:0 auto}

/* ── 头部 ── */
.header{background:linear-gradient(135deg,#0a1628,#0f3460 40%,#16213e 70%,#0a0e17);border:1px solid #1e3a5f;border-radius:16px;padding:24px 20px 20px;margin-bottom:12px;text-align:center;position:relative;overflow:hidden}
.header::before{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:radial-gradient(circle at 30% 30%,rgba(63,185,80,0.08),transparent 50%),radial-gradient(circle at 70% 70%,rgba(88,166,255,0.06),transparent 50%);animation:pulse 4s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:0.6}50%{opacity:1}}
.header h1{font-size:1.5em;font-weight:700;position:relative;z-index:1}
.header .sub{color:#8b949e;font-size:0.8em;margin-top:4px;position:relative;z-index:1}
.header .badge{display:inline-block;padding:3px 12px;border-radius:12px;font-size:0.72em;font-weight:600;margin-top:6px;position:relative;z-index:1}
.badge-bull{background:rgba(63,185,80,0.15);color:#3fb950}
.badge-bear{background:rgba(248,81,73,0.15);color:#f85149}
.badge-neutral{background:rgba(210,153,34,0.15);color:#d29922}

/* ── 输入区 ── */
.input-bar{display:flex;gap:8px;margin-bottom:12px;align-items:center;flex-wrap:wrap}
.input-bar input{flex:1;min-width:150px;padding:8px 14px;border-radius:10px;border:1px solid #1e3a5f;background:#131a26;color:#e6edf3;font-size:0.85em;outline:none;transition:border .2s}
.input-bar input:focus{border-color:#58a6ff}
.input-bar button{padding:8px 18px;border-radius:10px;background:#1e3a5f;color:#58a6ff;border:1px solid #58a6ff;font-size:0.85em;font-weight:600;cursor:pointer;transition:all .2s}
.input-bar button:hover{background:#58a6ff;color:#0a0e17}
.input-bar .quick-tags{display:flex;gap:6px;flex-wrap:wrap}
.input-bar .quick-tag{padding:4px 10px;border-radius:14px;border:1px solid #1e2d45;font-size:0.72em;color:#8b949e;cursor:pointer;transition:all .2s;background:#131a26}
.input-bar .quick-tag:hover{border-color:#58a6ff;color:#58a6ff}

/* ── 导航条 ── */
.nav-bar{display:flex;justify-content:center;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.nav-btn{font-size:0.7em;padding:5px 12px;border-radius:14px;background:#131a26;border:1px solid #1e2d45;color:#8b949e;text-decoration:none;transition:all .2s;display:inline-block}
.nav-btn:hover{border-color:#58a6ff;color:#58a6ff}
.nav-btn.active{border-color:#58a6ff;color:#58a6ff;background:rgba(88,166,255,0.1)}

/* ── Tab 切换 ── */
.tab-bar{display:flex;gap:4px;margin-bottom:14px;overflow-x:auto;padding-bottom:4px}
.tab-btn{padding:8px 16px;border-radius:8px 8px 0 0;border:1px solid transparent;font-size:0.78em;color:#8b949e;cursor:pointer;white-space:nowrap;transition:all .2s;background:transparent}
.tab-btn:hover{color:#c9d1d9;background:rgba(255,255,255,0.03)}
.tab-btn.active{color:#58a6ff;border-color:#1e2d45;border-bottom-color:#0a0e17;background:#131a26;font-weight:600}
.tab-content{display:none}
.tab-content.active{display:block}

/* ── KPI 网格 ── */
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px;margin-bottom:14px}
.kpi-card{background:#131a26;border:1px solid #1e2d45;border-radius:10px;padding:14px}
.kpi-card .kpi-label{color:#8b949e;font-size:0.66em;letter-spacing:0.5px;margin-bottom:4px}
.kpi-card .kpi-value{font-size:1.4em;font-weight:700;margin-bottom:2px}
.kpi-card .kpi-change{font-size:0.78em;margin-bottom:4px}
.kpi-card .kpi-note{font-size:0.68em;color:#6e7681;padding-top:5px;border-top:1px solid #1e2d45;line-height:1.4}

/* ── 模块卡片 ── */
.module{background:#131a26;border:1px solid #1e2d45;border-radius:12px;padding:16px;margin-bottom:14px}
.module-hdr{display:flex;align-items:center;gap:8px;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid #1e2d45}
.module-hdr .icon{font-size:1.1em}
.module-hdr h2{font-size:0.9em;font-weight:600;color:#58a6ff;flex:1}

/* ── 表格 ── */
table{width:100%;border-collapse:collapse;font-size:0.8em}
th,td{padding:6px 8px;text-align:left;border-bottom:1px solid #1e2d45}
th{color:#8b949e;font-weight:500;font-size:0.85em}
tr:hover{background:rgba(88,166,255,0.03)}
td.center{text-align:center}

/* ── 量化因子卡 ── */
.factor-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}
.factor-card{background:rgba(255,255,255,0.02);border:1px solid #1e2d45;border-radius:10px;padding:16px;text-align:center}
.factor-card .f-name{font-size:0.72em;color:#8b949e;margin-bottom:4px}
.factor-card .f-score{font-size:2em;font-weight:800;margin-bottom:4px}
.factor-card .f-detail{font-size:0.68em;color:#6e7681;line-height:1.5}
.factor-gauge{width:80px;height:80px;margin:0 auto 6px}

/* ── 相关性热力图 ── */
.corr-bar{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.corr-bar .cb-label{font-size:0.75em;color:#8b949e;width:80px;text-align:right;flex-shrink:0}
.corr-bar .cb-track{flex:1;height:10px;background:#1e2d45;border-radius:5px;overflow:hidden}
.corr-bar .cb-fill{height:100%;border-radius:5px;transition:width .3s}

/* ── 新闻列表 ── */
.news-item{display:flex;gap:8px;padding:7px 0;border-bottom:1px solid #1e2d45;align-items:flex-start}
.news-item:last-child{border-bottom:none}
.news-tag{font-size:0.65em;padding:2px 6px;border-radius:4px;flex-shrink:0;margin-top:2px}
.news-text{font-size:0.8em;line-height:1.4}
.news-meta{font-size:0.68em;color:#484f58;margin-top:2px}

/* ── 信号灯 ── */
.signal-box{padding:12px 16px;border-radius:8px;text-align:center;font-size:0.85em;font-weight:600;margin-bottom:10px}
.signal-box.bullish{background:rgba(63,185,80,0.08);border:1px solid rgba(63,185,80,0.2);color:#3fb950}
.signal-box.bearish{background:rgba(248,81,73,0.08);border:1px solid rgba(248,81,73,0.2);color:#f85149}
.signal-box.neutral{background:rgba(210,153,34,0.08);border:1px solid rgba(210,153,34,0.2);color:#d29922}

/* ── SVG图容器 ── */
.chart-box{background:rgba(255,255,255,0.01);border:1px solid #1e2d45;border-radius:8px;padding:12px;margin-bottom:12px;overflow-x:auto}

/* ── 页脚 ── */
.footer{text-align:center;padding:20px 0 40px;color:#484f58;font-size:0.7em;line-height:1.8}
.footer a{color:#58a6ff;text-decoration:none}

/* ── 响应式 ── */
@media(max-width:700px){
  body{padding:10px}
  .kpi-grid{grid-template-columns:repeat(2,1fr)}
  .factor-grid{grid-template-columns:repeat(2,1fr)}
  .tab-btn{padding:6px 10px;font-size:0.7em}
  .input-bar{flex-direction:column}
}
"""

# ═══════════════════════════════════════════
# JS (Tab切换 + SVG绘制)
# ═══════════════════════════════════════════

JS = r"""
function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelector('[data-tab="'+tabId+'"]').classList.add('active');
    document.getElementById(tabId).classList.add('active');
    if (tabId === 'tab3') drawTechChart();
}
function analyzeStock() {
    var code = document.getElementById('stockInput').value.trim();
    if (!code) return;
    code = code.replace(/[^0-9a-zA-Z]/g,'');
    window.location.href = 'stocks/' + code + '.html';
}
document.getElementById('stockInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') analyzeStock();
});

// SVG技术图表
function drawTechChart() {
    var svg = document.getElementById('tech-svg');
    if (!svg || svg.children.length > 1) return;
    var raw = svg.getAttribute('data-prices');
    if (!raw) return;
    var prices = raw.split(',').map(Number);
    var W = 760, H = 200, pad = 20, chartH = H - 40;
    var minP = Math.min.apply(null, prices) * 0.95;
    var maxP = Math.max.apply(null, prices) * 1.05;
    var range = maxP - minP || 1;
    function y(p) { return pad + chartH - ((p - minP) / range) * chartH; }
    function x(i) { return 40 + (i / (prices.length - 1)) * (W - 80); }
    
    var ns = 'http://www.w3.org/2000/svg';
    
    // 网格线
    for (var i = 0; i <= 4; i++) {
        var yy = pad + (chartH * i / 4);
        var line = document.createElementNS(ns, 'line');
        line.setAttribute('x1', 40); line.setAttribute('x2', W - 40);
        line.setAttribute('y1', yy); line.setAttribute('y2', yy);
        line.setAttribute('stroke', '#1e2d45'); line.setAttribute('stroke-width', '0.5');
        svg.appendChild(line);
        var txt = document.createElementNS(ns, 'text');
        txt.setAttribute('x', 34); txt.setAttribute('y', yy + 3);
        txt.setAttribute('text-anchor', 'end'); txt.setAttribute('font-size', '9');
        txt.setAttribute('fill', '#484f58');
        txt.textContent = '¥' + Math.round(maxP - (range * i / 4));
        svg.appendChild(txt);
    }
    
    // 价格线
    var pts = '';
    for (var i = 0; i < prices.length; i++) {
        pts += (i===0?'':' ') + x(i) + ',' + y(prices[i]);
    }
    var poly = document.createElementNS(ns, 'polyline');
    poly.setAttribute('points', pts);
    poly.setAttribute('fill', 'none');
    poly.setAttribute('stroke', '#58a6ff');
    poly.setAttribute('stroke-width', '1.5');
    svg.appendChild(poly);
    
    // 区域填充
    pts += ' ' + x(prices.length-1) + ',' + (pad+chartH) + ' ' + x(0) + ',' + (pad+chartH);
    var area = document.createElementNS(ns, 'polygon');
    area.setAttribute('points', pts);
    area.setAttribute('fill', 'rgba(88,166,255,0.08)');
    svg.appendChild(area);
}

// 打分环
function drawGauge(canvasId, score) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var w = canvas.width, h = canvas.height;
    var cx = w/2, cy = h/2, r = w/2 - 4;
    ctx.clearRect(0, 0, w, h);
    
    // 背景环
    ctx.beginPath(); ctx.arc(cx, cy, r, Math.PI, 0); ctx.lineWidth = 6;
    ctx.strokeStyle = '#1e2d45'; ctx.stroke();
    
    // 分数环
    var angle = Math.PI + (score / 100) * Math.PI;
    var grad = ctx.createLinearGradient(0, 0, w, 0);
    grad.addColorStop(0, '#f85149'); grad.addColorStop(0.5, '#d29922'); grad.addColorStop(1, '#3fb950');
    ctx.beginPath(); ctx.arc(cx, cy, r, Math.PI, angle); ctx.lineWidth = 6;
    ctx.strokeStyle = grad; ctx.stroke();
    
    // 分数文字
    ctx.fillStyle = '#e6edf3'; ctx.font = 'bold 18px sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(score, cx, cy - 2);
    ctx.font = '9px sans-serif'; ctx.fillStyle = '#8b949e';
    ctx.fillText('/100', cx, cy + 14);
}
"""

# ═══════════════════════════════════════════
# HTML构建函数
# ═══════════════════════════════════════════

def build_header(data):
    q = data.get("quote", {})
    meta = data.get("meta", {})
    alpha = data.get("alpha_factors", {})
    composite = alpha.get("composite", {})
    signal = composite.get("signal", "—")
    
    badge_class = "badge-bull" if "偏多" in signal else ("badge-bear" if "偏空" in signal or "看空" in signal else "badge-neutral")
    
    return f'''<div class="header">
    <h1>🧬 {q.get("name","—")} · Vibe-Trading 分析</h1>
    <div class="sub">{meta.get("market","")} | {q.get("price","—")} | {meta.get("generated_at","")}</div>
    <span class="badge {badge_class}">{signal}</span>
</div>'''


def build_input_bar(data):
    code = data.get("meta", {}).get("code", "")
    return f'''<div class="input-bar">
    <input type="text" id="stockInput" placeholder="输入股票代码 (如 300750 / 00700 / 600900)" value="{code}">
    <button onclick="analyzeStock()">🔍 分析</button>
    <div class="quick-tags">
        <span class="quick-tag" onclick="location.href='stocks/300750.html'">CATL</span>
        <span class="quick-tag" onclick="location.href='stocks/600900.html'">长江电力</span>
        <span class="quick-tag" onclick="location.href='stocks/00700.html'">腾讯</span>
        <span class="quick-tag" onclick="location.href='stocks/000001.html'">平安</span>
        <span class="quick-tag" onclick="location.href='stocks/600519.html'">茅台</span>
    </div>
</div>'''


def build_nav():
    return '''<div class="nav-bar">
    <a class="nav-btn" href="https://zxb20262026.github.io/300750/">🔋 宁德时代</a>
    <a class="nav-btn" href="https://zxb20262026.github.io/600900/">💧 长江电力</a>
    <a class="nav-btn" href="https://zxb20262026.github.io/00700/">🐧 腾讯控股</a>
    <a class="nav-btn" href="https://zxb20262026.github.io/sh300-etf-dashboard/">🎯 ETF雷达</a>
    <a class="nav-btn active" href="index.html">🧬 统一看板</a>
</div>'''


def build_tab_bar():
    tabs = [
        ("tab1", "📊 概览"),
        ("tab2", "🧮 估值"),
        ("tab3", "📈 技术"),
        ("tab4", "🔬 因子"),
        ("tab5", "🔥 相关"),
        ("tab6", "💰 资金"),
        ("tab7", "📰 资讯"),
    ]
    btns = "\n".join([f'<button class="tab-btn{" active" if i==0 else ""}" data-tab="{tid}" onclick="switchTab(\'{tid}\')">{label}</button>' for i, (tid, label) in enumerate(tabs)])
    return f'<div class="tab-bar">{btns}</div>'


# ── Tab 1: 概览仪表盘 ──
def build_tab1(data):
    q = data.get("quote", {})
    f = data.get("fundamentals", {})
    peg = data.get("peg", {})
    tech = data.get("tech", {})
    alpha = data.get("alpha_factors", {})
    ma_dev = data.get("ma_deviation", {})
    
    price = q.get("price", 0)
    chg = q.get("change_pct", 0)
    pe = f.get("pe_ttm", None)
    pb = f.get("pb", None)
    roe = f.get("roe", None)
    mcap = f.get("market_cap", None)
    
    # KPI 卡片
    cards = f'''
    <div class="kpi-card"><div class="kpi-label">最新价</div><div class="kpi-value" style="color:{color_pct(chg)}">¥{fmt(price)}</div><div class="kpi-change" style="color:{color_pct(chg)}">{sign(chg)}{fmt(chg)}%</div><div class="kpi-note">开盘 ¥{fmt(q.get("open"))}</div></div>
    <div class="kpi-card"><div class="kpi-label">PE(TTM)</div><div class="kpi-value" style="color:#58a6ff">{fmt(pe,1)}</div><div class="kpi-note">PB {fmt(pb,1)}x</div></div>
    <div class="kpi-card"><div class="kpi-label">PEG</div><div class="kpi-value" style="color:{peg.get('color','#8b949e')}">{fmt(peg.get('value'))}</div><div class="kpi-change" style="color:{peg.get('color','#8b949e')}">{peg.get('signal','—')}</div><div class="kpi-note">增长假设 {peg.get('growth_assumption','—')}%</div></div>
    <div class="kpi-card"><div class="kpi-label">ROE</div><div class="kpi-value" style="color:#3fb950">{fmt(roe,1)}%</div><div class="kpi-note">{'优秀' if roe and roe > 15 else ('良好' if roe and roe > 10 else '一般')}</div></div>
    <div class="kpi-card"><div class="kpi-label">总市值</div><div class="kpi-value" style="color:#8b949e">{fmt(mcap/100,1) if mcap else '—'}亿</div><div class="kpi-note">52周 {fmt(f.get("high_52w"))} / {fmt(f.get("low_52w"))}</div></div>
    <div class="kpi-card"><div class="kpi-label">成交额</div><div class="kpi-value" style="color:#8b949e">{fmt(q.get("amount",0)/1e8,1)}亿</div><div class="kpi-note">量 {fmt(q.get("volume",0)/1e4)}万手</div></div>
    <div class="kpi-card"><div class="kpi-label">MA5偏离</div><div class="kpi-value" style="color:{'#3fb950' if ma_dev.get('ma5',0) and ma_dev['ma5'] > 0 else '#f85149'}">{sign(ma_dev.get('ma5',0))}{fmt(abs(ma_dev.get('ma5',0)))}%</div><div class="kpi-note">MA5 ¥{fmt(tech.get('ma5'))}</div></div>
    <div class="kpi-card"><div class="kpi-label">RSI(14)</div><div class="kpi-value" style="color:{'#f85149' if tech.get('rsi',50) and tech['rsi'] > 70 else ('#3fb950' if tech.get('rsi',50) and tech['rsi'] < 30 else '#d29922')}">{fmt(tech.get('rsi'),1)}</div><div class="kpi-note">{'超买' if tech.get('rsi',50) and tech['rsi'] > 70 else ('超卖' if tech.get('rsi',50) and tech['rsi'] < 30 else '中性')}</div></div>
    '''
    
    # 综合信号
    composite = alpha.get("composite", {})
    sig_class = "bullish" if "偏多" in composite.get("signal","") else ("bearish" if "偏空" in composite.get("signal","") or "看空" in composite.get("signal","") else "neutral")
    
    signal_box = f'''<div class="signal-box {sig_class}">
    🧬 量化综合评分: <b>{composite.get('score','—')}/100</b> → {composite.get('signal','—')}
    </div>'''
    
    # PEG/MA 一句话
    summary_parts = []
    if peg.get("value") and peg["value"] < 1:
        summary_parts.append(f'PEG={peg["value"]} 低估区间')
    elif peg.get("value"):
        summary_parts.append(f'PEG={peg["value"]} 合理/偏高')
    
    if ma_dev.get("ma20") and abs(ma_dev["ma20"]) > 3:
        direction = "跌破" if ma_dev["ma20"] < 0 else "突破"
        summary_parts.append(f"{direction}MA20")
    
    if tech.get("macd", {}).get("signal") == "bullish":
        summary_parts.append("MACD金叉")
    
    summary_line = " · ".join(summary_parts) if summary_parts else "数据收集中..."
    
    return f'''<div class="kpi-grid">{cards}</div>
{signal_box}
<div class="module">
    <div class="module-hdr"><span class="icon">🧬</span><h2>Vibe信号摘要</h2></div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;font-size:0.8em">
        <div><span style="color:#8b949e">动量:</span> <b>{alpha.get("momentum",{}).get("score","—")}</b></div>
        <div><span style="color:#8b949e">价值:</span> <b>{alpha.get("value",{}).get("score","—")}</b></div>
        <div><span style="color:#8b949e">质量:</span> <b>{alpha.get("quality",{}).get("score","—")}</b></div>
    </div>
    <p style="margin-top:10px;font-size:0.78em;color:#c9d1d9;line-height:1.6">{summary_line}</p>
</div>'''


# ── Tab 2: 估值分析 ──
def build_tab2(data):
    f = data.get("fundamentals", {})
    peg = data.get("peg", {})
    q = data.get("quote", {})
    
    pe = f.get("pe_ttm")
    pb = f.get("pb")
    roe = f.get("roe")
    eps = f.get("eps_ttm")
    price = q.get("price", 0)
    
    # PE Bands简表
    bands = []
    if eps and eps > 0:
        for mult, label in [(15,"清仓"), (18,"止损"), (21,"保守"), (25,"合理"), (30,"偏高"), (35,"泡沫")]:
            bands.append((label, mult, round(eps * mult, 1)))
    
    band_rows = ""
    if bands:
        band_rows = "\n".join([f'<tr><td>{label}</td><td>{mult}x</td><td style="font-weight:600">{price_val}</td></tr>' for label, mult, price_val in bands])
    else:
        band_rows = '<tr><td colspan="3">EPS数据暂缺</td></tr>'
    
    # PEG 详细
    peg_detail = f'''
    <table>
        <tr><th>指标</th><th>数值</th><th>评估</th></tr>
        <tr><td>当前股价</td><td style="color:#58a6ff">¥{fmt(price)}</td><td></td></tr>
        <tr><td>PE(TTM)</td><td>{fmt(pe,1)}x</td><td>{'历史偏低' if pe and pe < 25 else ('合理' if pe and pe < 35 else '偏高')}</td></tr>
        <tr><td>PB</td><td>{fmt(pb,1)}x</td><td></td></tr>
        <tr><td>ROE</td><td>{fmt(roe,1)}%</td><td></td></tr>
        <tr><td>EPS(TTM)</td><td>¥{fmt(eps,1)}</td><td></td></tr>
        <tr><td>PEG</td><td style="color:{peg.get('color','#8b949e')};font-weight:700">{fmt(peg.get('value'))}</td><td>{peg.get('signal','—')}</td></tr>
    </table>
    <div class="signal-box {'bullish' if peg.get('value') and peg['value'] < 1 else 'neutral'}" style="margin-top:12px">
        PEG={fmt(peg.get('value'))} · 增长假设{peg.get('growth_assumption','—')}% · {peg.get('signal','—')}
    </div>
    '''
    
    return f'''<div class="module">
    <div class="module-hdr"><span class="icon">📏</span><h2>PE Bands 估值区间</h2></div>
    <table><tr><th>情景</th><th>PE</th><th>目标价(基于EPS ¥{fmt(eps,1)})</th></tr>{band_rows}</table>
    <p style="font-size:0.72em;color:#6e7681;margin-top:4px">当前PE={fmt(pe,1)}x · 合理PE区间 20-30x</p>
</div>
<div class="module">
    <div class="module-hdr"><span class="icon">🧮</span><h2>PEG估值详解</h2></div>
    {peg_detail}
</div>'''


# ── Tab 3: 技术面 ──
def build_tab3(data):
    tech = data.get("tech", {})
    q = data.get("quote", {})
    klines = tech.get("klines_90d", [])
    
    price = q.get("price", 0)
    ma5 = tech.get("ma5")
    ma20 = tech.get("ma20")
    ma60 = tech.get("ma60")
    rsi = tech.get("rsi")
    macd = tech.get("macd", {})
    
    # 技术卡片
    def ma_status(val, price, name):
        if val is None: return "—", "#8b949e"
        dev = (price - val) / val * 100
        if abs(dev) < 1: return f"贴近{name}", "#58a6ff"
        elif dev > 0: return f"站上{name}", "#3fb950"
        else: return f"跌破{name}", "#f85149"
    
    s5, c5 = ma_status(ma5, price, "MA5")
    s20, c20 = ma_status(ma20, price, "MA20")
    s60, c60 = ma_status(ma60, price, "MA60")
    
    cards = f'''
    <div class="factor-grid" style="grid-template-columns:repeat(4,1fr)">
        <div class="factor-card"><div class="f-name">MA5</div><div class="f-score" style="font-size:1.3em;color:{c5}">{s5}</div><div class="f-detail">{fmt(ma5)}</div></div>
        <div class="factor-card"><div class="f-name">MA20</div><div class="f-score" style="font-size:1.3em;color:{c20}">{s20}</div><div class="f-detail">{fmt(ma20)}</div></div>
        <div class="factor-card"><div class="f-name">MA60</div><div class="f-score" style="font-size:1.3em;color:{c60}">{s60}</div><div class="f-detail">{fmt(ma60)}</div></div>
        <div class="factor-card"><div class="f-name">MACD</div><div class="f-score" style="font-size:1.3em;color:{'#3fb950' if macd.get('bar',0) > 0 else '#f85149'}">{'金叉' if macd.get('signal')=='bullish' else '死叉'}</div><div class="f-detail">DIF{fmt(macd.get('dif'))} BAR{fmt(macd.get('bar'))}</div></div>
    </div>
    '''
    
    # SVG 价格图 (用data属性存储价格，JS绘制)
    price_list = ",".join([str(k["close"]) for k in klines[-90:]])
    chart = f'<div class="chart-box"><svg id="tech-svg" viewBox="0 0 780 220" style="width:100%;height:auto;max-height:240px" data-prices="{price_list}"></svg></div>'
    
    # 技术研判
    diagnosis = []
    if ma60 and price < ma60 * 0.95:
        diagnosis.append(f'<li><span style="color:#f85149">⚠️ 跌破MA60({fmt(ma60)})，偏离{fmt((price-ma60)/ma60*100,1)}%，中长期趋势偏弱</span></li>')
    elif ma60 and price > ma60:
        diagnosis.append(f'<li><span style="color:#3fb950">✅ 站上MA60({fmt(ma60)})，中长期趋势偏强</span></li>')
    
    if rsi and rsi > 70:
        diagnosis.append(f'<li><span style="color:#f85149">RSI={rsi}，超买区域</span></li>')
    elif rsi and rsi < 30:
        diagnosis.append(f'<li><span style="color:#3fb950">RSI={rsi}，超卖区域，可能反弹</span></li>')
    else:
        diagnosis.append(f'<li>RSI={fmt(rsi,1)}，中性区间</li>')
    
    if macd.get("signal") == "bullish":
        diagnosis.append(f'<li><span style="color:#3fb950">MACD金叉，短线偏多</span></li>')
    else:
        diagnosis.append(f'<li><span style="color:#f85149">MACD死叉，短线偏空</span></li>')
    
    return f'''{cards}
{chart}
<div class="module">
    <div class="module-hdr"><span class="icon">📝</span><h2>技术面研判</h2></div>
    <ul style="list-style:none;font-size:0.8em;line-height:1.8">{chr(10).join(diagnosis)}</ul>
</div>'''


# ── Tab 4: 量化因子 ──
def build_tab4(data):
    alpha = data.get("alpha_factors", {})
    mom = alpha.get("momentum", {})
    val = alpha.get("value", {})
    qual = alpha.get("quality", {})
    comp = alpha.get("composite", {})
    
    # Canvas gauges
    def gauge_html(canvas_id, score, label, detail=""):
        return f'''<div class="factor-card">
    <div class="f-name">{label}</div>
    <canvas id="{canvas_id}" width="80" height="80" class="factor-gauge"></canvas>
    <div style="font-size:1.3em;font-weight:700;color:{'#3fb950' if score >= 70 else ('#d29922' if score >= 50 else '#f85149')}">{score}</div>
    <div class="f-detail">{detail}</div>
</div>'''
    
    factors_html = f'''<div class="factor-grid">
    {gauge_html("gauge-mom", mom.get("score", 50), "📈 动量因子", f"5日 {sign(mom.get('mom_5d',0))}{fmt(abs(mom.get('mom_5d',0)))}%<br>20日 {sign(mom.get('mom_20d',0))}{fmt(abs(mom.get('mom_20d',0)))}%")}
    {gauge_html("gauge-val", val.get("score", 50), "💰 价值因子", f"PE {fmt(val.get('pe'),1)}x<br>PB {fmt(val.get('pb'),1)}x<br>PEG {fmt(val.get('peg'))}")}
    {gauge_html("gauge-qual", qual.get("score", 50), "🏆 质量因子", f"ROE {fmt(qual.get('roe'),1)}%")}
    {gauge_html("gauge-comp", comp.get("score", 50), "🧬 综合评分", comp.get('signal','—'))}
</div>'''
    
    # 信号灯
    sig_class = "bullish" if "偏多" in comp.get("signal","") else ("bearish" if "偏空" in comp.get("signal","") or "看空" in comp.get("signal","") else "neutral")
    
    # 方法说明
    method = '''<div class="module" style="margin-top:10px">
    <div class="module-hdr"><span class="icon">📖</span><h2>因子方法论 (Vibe-Trading Alpha Zoo 启发)</h2></div>
    <div style="font-size:0.78em;color:#8b949e;line-height:1.8">
        <p>📈 <b>动量因子 (40%)</b>: 基于5/20/60日多周期价格动量，捕捉趋势强度</p>
        <p>💰 <b>价值因子 (35%)</b>: PE/PB估值分位数 + PEG，评估估值吸引力</p>
        <p>🏆 <b>质量因子 (25%)</b>: ROE + 价格波动率，衡量盈利质量与稳定性</p>
        <p style="margin-top:8px;color:#6e7681">评分范围 0-100，≥70偏多，50-70中性，<50偏空</p>
    </div>
</div>'''
    
    return f'''{factors_html}
<div class="signal-box {sig_class}">
    🧬 Vibe-Trading 综合评分: <b>{comp.get('score','—')}/100</b> → {comp.get('signal','—')}
    <br><span style="font-size:0.78em;font-weight:400;color:#8b949e">动量{comp.get('score',0)*0.4:.0f} + 价值{comp.get('score',0)*0.35:.0f} + 质量{comp.get('score',0)*0.25:.0f}</span>
</div>
{method}
<script>setTimeout(function(){{drawGauge('gauge-mom',{mom.get('score',50)});drawGauge('gauge-val',{val.get('score',50)});drawGauge('gauge-qual',{qual.get('score',50)});drawGauge('gauge-comp',{comp.get('score',50)});}},200);</script>'''


# ── Tab 5: 相关性 ──
def build_tab5(data):
    corr = data.get("correlation", {})
    correlations = corr.get("correlations", [])
    vol = corr.get("volatility_annual", 0)
    mdd = corr.get("max_drawdown_90d", 0)
    
    # 相关条
    corr_bars = ""
    for c in correlations:
        corr_val = c.get("correlation", 0)
        abs_val = abs(corr_val)
        width = min(abs_val * 100, 100)
        color = "#3fb950" if corr_val > 0.5 else ("#f85149" if corr_val < -0.5 else "#d29922")
        corr_bars += f'''<div class="corr-bar">
    <span class="cb-label">{c['name']}</span>
    <div class="cb-track"><div class="cb-fill" style="width:{width}%;background:{color}"></div></div>
    <span style="font-size:0.75em;color:{color};width:40px;text-align:right">{corr_val:+.3f}</span>
</div>'''
    
    return f'''<div class="module">
    <div class="module-hdr"><span class="icon">🔥</span><h2>相关性分析</h2></div>
    {corr_bars if corr_bars else '<p style="color:#8b949e;font-size:0.8em">暂无相关性数据</p>'}
</div>
<div class="module">
    <div class="module-hdr"><span class="icon">⚠️</span><h2>风险指标</h2></div>
    <div class="kpi-grid" style="grid-template-columns:repeat(2,1fr)">
        <div class="kpi-card"><div class="kpi-label">年化波动率</div><div class="kpi-value" style="color:#d29922">{fmt(vol,1)}%</div><div class="kpi-note">近90日日收益标准差年化</div></div>
        <div class="kpi-card"><div class="kpi-label">最大回撤(90日)</div><div class="kpi-value" style="color:#f85149">{fmt(mdd,1)}%</div><div class="kpi-note">{'高风险' if mdd > 20 else ('中等风险' if mdd > 10 else '低风险')}</div></div>
    </div>
</div>'''


# ── Tab 6: 资金面 ──
def build_tab6(data):
    fund_flow = data.get("fund_flow") or []
    q = data.get("quote", {})
    
    flow_rows = ""
    if fund_flow:
        for item in fund_flow[:5]:
            inflow = item.get("main_inflow", 0)
            c = "#f85149" if inflow > 0 else "#3fb950"
            flow_rows += f'<tr><td>{item.get("date","")}</td><td style="color:{c};font-weight:600">{sign(inflow)}{fmt(inflow)}亿</td></tr>'
    else:
        flow_rows = '<tr><td colspan="2" style="color:#8b949e">暂无主力资金数据 (港股或数据源不可用)</td></tr>'
    
    return f'''<div class="module">
    <div class="module-hdr"><span class="icon">💰</span><h2>主力资金流向</h2></div>
    <table><tr><th>日期</th><th>主力净流入(亿)</th></tr>{flow_rows}</table>
</div>
<div class="module">
    <div class="module-hdr"><span class="icon">📊</span><h2>今日成交</h2></div>
    <div class="kpi-grid" style="grid-template-columns:repeat(2,1fr)">
        <div class="kpi-card"><div class="kpi-label">成交额</div><div class="kpi-value">{fmt(q.get('amount',0)/1e8,1)}亿</div></div>
        <div class="kpi-card"><div class="kpi-label">成交量</div><div class="kpi-value">{fmt(q.get('volume',0)/1e4)}万手</div></div>
    </div>
</div>'''


# ── Tab 7: 资讯情绪 ──
def build_tab7(data):
    news = data.get("news") or {}
    items = news.get("items", []) if news else []
    sentiment = news.get("sentiment", 0)
    
    news_html = ""
    if items:
        for n in items[:8]:
            title = n.get("title", "")
            # 简单情绪标签
            pos_words = ["涨","利好","增长","突破","买入","增持","超预期"]
            neg_words = ["跌","利空","下滑","亏损","减持","下降","暴雷"]
            is_pos = any(w in title for w in pos_words)
            is_neg = any(w in title for w in neg_words)
            tag = "🟢" if is_pos else ("🔴" if is_neg else "⚪")
            tag_class = "background:rgba(63,185,80,0.1);color:#3fb950" if is_pos else ("background:rgba(248,81,73,0.1);color:#f85149" if is_neg else "background:rgba(139,148,158,0.1);color:#8b949e")
            
            news_html += f'''<div class="news-item">
    <span class="news-tag" style="{tag_class}">{tag}</span>
    <div class="news-text">
        <a href="{n.get('url','#')}" target="_blank" style="color:#e6edf3;text-decoration:none">{title}</a>
        <div class="news-meta">{n.get('date','')}</div>
    </div>
</div>'''
    else:
        news_html = '<p style="color:#8b949e;font-size:0.8em;padding:16px">暂无新闻数据</p>'
    
    sent_color = "#3fb950" if sentiment > 20 else ("#f85149" if sentiment < -20 else "#d29922")
    
    return f'''<div class="module">
    <div class="module-hdr"><span class="icon">📰</span><h2>资讯情绪</h2></div>
    <div class="signal-box {'bullish' if sentiment > 20 else ('bearish' if sentiment < -20 else 'neutral')}" style="margin-bottom:12px">
        📊 情绪评分: <b style="color:{sent_color}">{sentiment:+d}</b> / 100 · {news.get('total',0)}条新闻
    </div>
    {news_html}
</div>'''


# ═══════════════════════════════════════════
# 主生成函数
# ═══════════════════════════════════════════

def generate(data):
    tabs = {
        "tab1": build_tab1(data),
        "tab2": build_tab2(data),
        "tab3": build_tab3(data),
        "tab4": build_tab4(data),
        "tab5": build_tab5(data),
        "tab6": build_tab6(data),
        "tab7": build_tab7(data),
    }
    
    tab_panels = "\n".join([f'<div class="tab-content{" active" if i==0 else ""}" id="{tid}">{content}</div>' for i, (tid, content) in enumerate(tabs.items())])
    
    meta = data.get("meta", {})
    
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>🧬 {data.get("quote",{}).get("name","Vibe-Trading")} · 统一看板</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
{build_nav()}
{build_header(data)}
{build_input_bar(data)}
{build_tab_bar()}
{tab_panels}
<div class="footer">
    🤖 Vibe-Trading 统一看板 v1.0 · 数据: 新浪/腾讯/东方财富<br>
    {meta.get("generated_at","")} · 7维度分析<br>
    ⚠️ 仅供参考 不构成投资建议
</div>
</div>
<script>{JS}</script>
</body>
</html>'''


def main():
    if len(sys.argv) < 2:
        print("用法: python3 gen_unified.py <股票代码>")
        sys.exit(1)
    
    code = sys.argv[1]
    src_dir = os.path.dirname(__file__)
    json_file = os.path.join(src_dir, "stocks", f"{code}.json")
    
    # 如果JSON不存在，先采集
    if not os.path.exists(json_file):
        print(f"📡 数据文件不存在，正在采集 {code}...")
        analyze_script = os.path.join(src_dir, "analyze.py")
        ret = os.system(f"cd {src_dir} && python3 analyze.py {code}")
        if ret != 0:
            print("❌ 数据采集失败")
            sys.exit(1)
    
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    html = generate(data)
    
    out_file = os.path.join(src_dir, "stocks", f"{code}.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✅ 已生成: {out_file}")
    print(f"   文件大小: {os.path.getsize(out_file):,} bytes")


if __name__ == "__main__":
    main()
