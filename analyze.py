#!/usr/bin/env python3
"""
Vibe-Trading 统一分析引擎 v1.0
支持任意A股/港股代码 → 7维度数据采集+量化计算
用法: python3 analyze.py 300750  → 输出 stocks/300750.json
      python3 analyze.py 00700   → 输出 stocks/00700.json
"""

import urllib.request, ssl, json, re, time, statistics, math, sys, os
from datetime import datetime, timedelta

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

H_SINA = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"}
H_EM = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.eastmoney.com/"}
H_TX = {"User-Agent": "Mozilla/5.0", "Referer": "https://web.ifzq.gtimg.cn/"}

def get(url, enc="utf-8", t=10, headers=None):
    req = urllib.request.Request(url, headers=headers or H_SINA)
    return urllib.request.urlopen(req, timeout=t, context=ssl_ctx).read().decode(enc, errors="replace")

def get_json(url, t=10, headers=None):
    return json.loads(get(url, t=t, headers=headers or H_EM))

# ═══════════════════════════════════════════
# 市场检测 + 代码标准化
# ═══════════════════════════════════════════

def detect_market(code):
    """检测市场并返回标准化的API代码"""
    code = str(code).strip().upper()
    
    # 港股: 5位数字 → hkXXXXX (补齐到5位)
    if code.isdigit() and len(code) <= 5:
        code = code.zfill(5)
        return "hk", code, f"hk{code}"
    
    # A股: sh/sz前缀
    if code.startswith("SH") or code.startswith("60"):
        num = code.replace("SH", "").replace("sh", "")
        return "a", num, f"sh{num}"
    if code.startswith("SZ") or code.startswith("00") or code.startswith("30"):
        num = code.replace("SZ", "").replace("sz", "")
        return "a", num, f"sz{num}"
    
    # 6位数字 → A股
    if code.isdigit() and len(code) == 6:
        prefix = "sh" if code.startswith("6") else "sz"
        return "a", code, f"{prefix}{code}"
    
    return "unknown", code, code

# ═══════════════════════════════════════════
# 模块1: 实时行情 + 基本面
# ═══════════════════════════════════════════

def fetch_quote(market, api_code):
    """获取实时行情"""
    try:
        if market == "a":
            url = f"https://hq.sinajs.cn/list={api_code}"
            raw = get(url, "gbk")
        else:
            url = f"https://hq.sinajs.cn/list={api_code}"
            raw = get(url, "gbk")
        
        m = re.search(r'"(.+?)"', raw)
        if not m: return None
        p = m.group(1).split(",")
        if len(p) < 10: return None
        
        # A股字段: name[0], open[1], prev[2], price[3], high[4], low[5], ... vol[8], amt[9]
        # 港股字段: ename[0], name[1], ... open[2], prev[3], price[4], ... (偏移+1)
        if market == "hk":
            name = p[1] if len(p) > 1 else p[0]
            price = float(p[6]) if len(p) > 6 and p[6] else 0
            prev = float(p[3]) if len(p) > 3 and p[3] else 0
            open_p = float(p[2]) if len(p) > 2 and p[2] else 0
            high = float(p[4]) if len(p) > 4 and p[4] else 0
            low = float(p[5]) if len(p) > 5 and p[5] else 0
            vol = int(float(p[12]) if len(p) > 12 and p[12] else 0)
            amt = float(p[13]) if len(p) > 13 and p[13] else 0
            change_pct = float(p[8]) if len(p) > 8 and p[8] else 0
        else:
            name = p[0]
            price = float(p[3]) if p[3] else 0
            prev = float(p[2]) if p[2] else 0
            open_p = float(p[1]) if p[1] else 0
            high = float(p[4]) if p[4] else 0
            low = float(p[5]) if p[5] else 0
            vol = int(p[8]) if p[8] else 0
            amt = float(p[9]) if p[9] else 0
            change_pct = round((price - prev) / prev * 100, 2) if prev else 0
        
        return {
            "name": name, "price": round(price, 2), "prev_close": round(prev, 2),
            "open": round(open_p, 2), "high": round(high, 2), "low": round(low, 2),
            "volume": vol, "amount": amt if amt else 0,
            "change": round(price - prev, 2),
            "change_pct": change_pct,
        }
    except Exception as e:
        print(f"  ⚠️ fetch_quote error: {e}")
        return None


def fetch_fundamentals(market, api_code):
    """获取PE/PB/ROE/市值/52周高低/股息率/EPS"""
    try:
        raw = get(f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={api_code},day,,,1,qfq", headers=H_TX)
        d = json.loads(raw)
        qt = d.get("data", {}).get(api_code, {}).get("qt", {}).get(api_code, [])
        
        result = {}
        # 腾讯qt字段索引:
        # qt[39]=PE(TTM), qt[46]=PB, qt[45]=市值(亿), qt[65]=ROE
        # 港股和A股字段相同，但名称可能是英文
        if len(qt) > 39 and qt[39]:
            try:
                result["pe_ttm"] = float(qt[39])
            except (ValueError, TypeError):
                pass
        if len(qt) > 46 and qt[46]:
            try:
                result["pb"] = float(qt[46])
            except (ValueError, TypeError):
                pass
        if len(qt) > 45 and qt[45]:
            try:
                result["market_cap"] = float(qt[45])
            except (ValueError, TypeError):
                pass
        if len(qt) > 65 and qt[65]:
            try:
                result["roe"] = float(qt[65])
            except (ValueError, TypeError):
                pass
        if len(qt) > 49 and qt[49]:
            try: result["high_52w"] = float(qt[49])
            except: pass
        if len(qt) > 50 and qt[50]:
            try: result["low_52w"] = float(qt[50])
            except: pass
        if len(qt) > 55 and qt[55]:
            try: result["div_yield"] = float(qt[55])
            except: pass
        if len(qt) > 43 and qt[43]:
            try: result["eps_ttm"] = float(qt[43])
            except: pass
        
        return result if result else None
    except Exception as e:
        print(f"  ⚠️ fetch_fundamentals error: {e}")
        return None


def fetch_kline(market, api_code, days=90):
    """获取K线数据"""
    try:
        raw = get(f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={api_code},day,,,{days},qfq", headers=H_TX)
        d = json.loads(raw)
        stock_data = d.get("data", {}).get(api_code, {})
        klines = stock_data.get("qfqday", []) or stock_data.get("day", [])
        
        result = []
        for k in klines:
            if isinstance(k, (list, tuple)) and len(k) >= 6:
                try:
                    result.append({
                        "date": str(k[0]),
                        "open": float(k[1]), "close": float(k[2]),
                        "high": float(k[3]), "low": float(k[4]),
                        "volume": float(k[5]) if k[5] else 0
                    })
                except (ValueError, TypeError):
                    continue
        return result
    except Exception as e:
        print(f"  ⚠️ fetch_kline error: {e}")
        return []

# ═══════════════════════════════════════════
# 模块2: Vibe-Trading 量化计算
# ═══════════════════════════════════════════

def calc_ma(klines, period):
    """计算移动平均线"""
    if len(klines) < period:
        return None
    closes = [k["close"] for k in klines[-period:]]
    return round(sum(closes) / len(closes), 2)


def calc_rsi(klines, period=14):
    """计算RSI"""
    if len(klines) < period + 1:
        return None
    closes = [k["close"] for k in klines]
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def calc_macd(klines):
    """计算MACD (12,26,9)"""
    if len(klines) < 26:
        return None
    closes = [k["close"] for k in klines]
    
    def ema(data, period):
        if len(data) < period:
            return None
        multiplier = 2 / (period + 1)
        ema_val = sum(data[:period]) / period
        for price in data[period:]:
            ema_val = (price - ema_val) * multiplier + ema_val
        return ema_val
    
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    
    if ema12 is None or ema26 is None:
        return None
    
    dif = round(ema12 - ema26, 3)
    
    # DEA (signal line)
    difs = []
    for i in range(26, len(closes) + 1):
        e12 = ema(closes[:i], 12)
        e26 = ema(closes[:i], 26)
        if e12 and e26:
            difs.append(e12 - e26)
    
    dea = round(sum(difs[-9:]) / 9, 3) if len(difs) >= 9 else dif
    bar = round((dif - dea) * 2, 3)
    
    return {"dif": dif, "dea": dea, "bar": bar, "signal": "bullish" if bar > 0 else "bearish"}


def calc_alpha_factors(klines, fundamentals):
    """计算量化因子评分 (Vibe-Trading Alpha Zoo 启发)
    
    三大类因子:
    - 动量因子 (40%): 短期/中期/长期动量 + 成交量动量
    - 价值因子 (35%): PE分位 + PB分位 + PEG
    - 质量因子 (25%): ROE + 毛利率稳定性 + 盈利增长
    """
    if len(klines) < 60:
        return None
    
    closes = [k["close"] for k in klines]
    current = closes[-1]
    
    # ── 动量因子 ──
    mom_5d = (current / closes[-6] - 1) * 100 if len(closes) >= 6 else 0
    mom_20d = (current / closes[-21] - 1) * 100 if len(closes) >= 21 else 0
    mom_60d = (current / closes[-61] - 1) * 100 if len(closes) >= 61 else 0
    
    # 动量得分 (0-100)
    mom_score = 50
    mom_score += min(max(mom_5d * 5, -20), 20)
    mom_score += min(max(mom_20d * 1.5, -15), 15)
    mom_score += min(max(mom_60d * 0.5, -15), 15)
    mom_score = max(0, min(100, mom_score))
    
    # ── 价值因子 ──
    pe = fundamentals.get("pe_ttm", 25) if fundamentals else 25
    pb = fundamentals.get("pb", 3) if fundamentals else 3
    roe = fundamentals.get("roe", 10) if fundamentals else 10
    
    # PE得分 (PE越低得分越高, A股合理PE≈20-30)
    if pe <= 0:
        pe_score = 30
    elif pe < 15:
        pe_score = 90
    elif pe < 20:
        pe_score = 75
    elif pe < 25:
        pe_score = 60
    elif pe < 35:
        pe_score = 40
    elif pe < 50:
        pe_score = 20
    else:
        pe_score = 10
    
    # PB得分
    if pb <= 1:
        pb_score = 85
    elif pb <= 2:
        pb_score = 65
    elif pb <= 4:
        pb_score = 45
    elif pb <= 8:
        pb_score = 25
    else:
        pb_score = 10
    
    # PEG (需要估算增长率)
    if pe > 0 and roe > 0:
        est_growth = min(roe * 0.8, 40)  # 保守估计增长率
        peg = round(pe / est_growth, 2)
    else:
        peg = None
    
    peg_score = 70 if peg and peg < 1 else (50 if peg and peg < 1.5 else 30)
    
    value_score = round(pe_score * 0.4 + pb_score * 0.3 + peg_score * 0.3)
    
    # ── 质量因子 ──
    roe_score = min(100, max(0, roe * 3.5)) if roe else 50
    
    # 盈利稳定性 (价格波动代理)
    if len(closes) >= 20:
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, min(60, len(closes)))]
        if returns:
            volatility = statistics.stdev(returns) * math.sqrt(252) * 100
            stability_score = max(10, min(100, 100 - volatility * 2))
        else:
            stability_score = 50
    else:
        stability_score = 50
    
    quality_score = round(roe_score * 0.5 + stability_score * 0.5)
    
    # ── 综合得分 ──
    composite = round(mom_score * 0.4 + value_score * 0.35 + quality_score * 0.25)
    
    # 信号判断
    if composite >= 70:
        signal = "🟢 偏多"
        signal_color = "#3fb950"
    elif composite >= 50:
        signal = "🟡 中性"
        signal_color = "#d29922"
    elif composite >= 30:
        signal = "🟠 偏空"
        signal_color = "#f0883e"
    else:
        signal = "🔴 看空"
        signal_color = "#f85149"
    
    return {
        "momentum": {
            "score": round(mom_score), "mom_5d": round(mom_5d, 2),
            "mom_20d": round(mom_20d, 2), "mom_60d": round(mom_60d, 2),
        },
        "value": {
            "score": value_score, "pe": pe, "pb": pb, "peg": peg,
        },
        "quality": {
            "score": quality_score, "roe": roe,
        },
        "composite": {
            "score": composite, "signal": signal, "color": signal_color,
        }
    }


def calc_correlation(klines, market):
    """计算与主要指数的相关性
    
    简化版: 用价格动量的同步性作为相关代理
    """
    if len(klines) < 20:
        return None
    
    closes = [k["close"] for k in klines]
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    
    # 获取指数K线 (上证/恒生)
    if market == "a":
        bench_code = "sh000001"
    else:
        bench_code = "hkHSI"
    
    bench_kline = fetch_kline(market, bench_code, len(klines))
    
    correlations = []
    
    # 大盘相关性
    if bench_kline and len(bench_kline) >= 20:
        bench_closes = [k["close"] for k in bench_kline]
        bench_returns = [(bench_closes[i] - bench_closes[i-1]) / bench_closes[i-1] for i in range(1, len(bench_closes))]
        
        min_len = min(len(returns), len(bench_returns))
        if min_len > 5:
            r = returns[-min_len:]
            br = bench_returns[-min_len:]
            corr = statistics.correlation(r, br) if len(r) > 1 else 0
            correlations.append({
                "name": "上证指数" if market == "a" else "恒生指数",
                "correlation": round(corr, 3),
                "beta": round(corr * (statistics.stdev(r) / statistics.stdev(br)) if statistics.stdev(br) > 0 else 1, 2)
            })
    
    # 计算与其他常见基准的相关性 (模拟 - 用自相关作为代理)
    # 实际应该获取板块指数数据，这里做简化版本
    auto_corr_lag1 = statistics.correlation(returns[:-1], returns[1:]) if len(returns) > 2 else 0
    
    correlations.append({
        "name": "自相关(1日)", "correlation": round(auto_corr_lag1, 3), "beta": 0
    })
    
    return {
        "correlations": correlations,
        "volatility_annual": round(statistics.stdev(returns) * math.sqrt(252) * 100, 1) if returns else 0,
        "max_drawdown_90d": round(calc_max_drawdown(closes), 1)
    }


def calc_max_drawdown(prices):
    """计算最大回撤"""
    if len(prices) < 2:
        return 0
    peak = prices[0]
    max_dd = 0
    for p in prices:
        if p > peak:
            peak = p
        dd = (peak - p) / peak * 100
        max_dd = max(max_dd, dd)
    return max_dd


# ═══════════════════════════════════════════
# 模块3: 资金面 + 资讯
# ═══════════════════════════════════════════

def fetch_fund_flow(market, code):
    """获取资金流向 (东财)"""
    try:
        if market != "a":
            return None
        secid = f"0.{code}" if code.startswith("0") or code.startswith("3") else f"1.{code}"
        url = f"https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?secid={secid}&fields1=f1&fields2=f51,f52,f53,f54,f55&lmt=5"
        data = get_json(url)
        flows = []
        for line in data.get("data", {}).get("klines", []):
            parts = line.split(",")
            if len(parts) >= 5:
                flows.append({
                    "date": parts[0],
                    "main_inflow": round(float(parts[1]) / 10000, 2),  # 亿
                })
        return flows
    except:
        return None


def fetch_news(market, code, name=""):
    """获取新闻 (东财搜索)"""
    try:
        if market == "a":
            search_code = f"{code}"
        else:
            search_code = code
        
        keyword = name if name else code
        url = f"https://search-api-web.eastmoney.com/search/jsonp?cb=jQuery&param={{\"uid\":\"\",\"keyword\":\"{keyword}\",\"type\":[\"8196\"],\"client\":\"web\",\"pageIndex\":1,\"pageSize\":10}}"
        raw = get(url, headers=H_EM)
        # 简单提取
        titles = re.findall(r'"title":"(.*?)"', raw)
        dates = re.findall(r'"date":"(.*?)"', raw)
        urls = re.findall(r'"url":"(.*?)"', raw)
        
        news = []
        for i in range(min(len(titles), 8)):
            news.append({
                "title": titles[i].replace("\\u0026", "&"),
                "date": dates[i][:10] if i < len(dates) else "",
                "url": urls[i] if i < len(urls) else "#"
            })
        
        # 简单情绪评分
        positive_words = ["涨", "利好", "增长", "突破", "买入", "增持", "超预期", "创新高", "龙头", "领先"]
        negative_words = ["跌", "利空", "下滑", "亏损", "减持", "下降", "暴雷", "处罚", "风险", "退市"]
        
        pos_count = sum(1 for n in news for w in positive_words if w in n["title"])
        neg_count = sum(1 for n in news for w in negative_words if w in n["title"])
        
        sentiment = round((pos_count - neg_count) / max(len(news), 1) * 100)
        sentiment = max(-100, min(100, sentiment))
        
        return {"items": news, "sentiment": sentiment, "total": len(news)}
    except:
        return None


# ═══════════════════════════════════════════
# 模块4: 主采集入口
# ═══════════════════════════════════════════

def analyze(code):
    """统一分析入口"""
    print(f"\n{'='*60}")
    print(f"🔍 Vibe-Trading 分析引擎 · 代码: {code}")
    print(f"{'='*60}")
    
    market, num, api_code = detect_market(code)
    if market == "unknown":
        print(f"❌ 无法识别代码: {code}")
        return None
    
    market_name = "A股" if market == "a" else "港股"
    print(f"📌 市场: {market_name} | API代码: {api_code}")
    
    # Step 1: 实时行情
    print("  [1/6] 实时行情...")
    quote = fetch_quote(market, api_code)
    if not quote:
        print("  ❌ 行情获取失败")
        return None
    print(f"  ✅ {quote['name']} ¥{quote['price']} {quote['change_pct']:+.2f}%")
    
    # Step 2: 基本面
    print("  [2/6] 基本面数据...")
    fundamentals = fetch_fundamentals(market, api_code)
    if fundamentals:
        pe_str = f"PE={fundamentals.get('pe_ttm','?')}" if fundamentals.get('pe_ttm') else ""
        print(f"  ✅ {pe_str} PB={fundamentals.get('pb','?')} ROE={fundamentals.get('roe','?')}%")
    
    # Step 3: K线 + 技术指标
    print("  [3/6] K线 + 技术指标...")
    klines = fetch_kline(market, api_code, 90)
    print(f"  ✅ {len(klines)} 根K线")
    
    ma5 = calc_ma(klines, 5)
    ma20 = calc_ma(klines, 20)
    ma60 = calc_ma(klines, 60)
    rsi = calc_rsi(klines)
    macd = calc_macd(klines)
    
    tech = {
        "ma5": ma5, "ma20": ma20, "ma60": ma60,
        "rsi": rsi, "macd": macd,
        "klines_90d": klines[-90:] if len(klines) > 90 else klines
    }
    
    # Step 4: 量化因子
    print("  [4/6] Vibe-Trading 量化因子...")
    alpha = calc_alpha_factors(klines, fundamentals)
    if alpha:
        print(f"  ✅ 动量{alpha['momentum']['score']} | 价值{alpha['value']['score']} | 质量{alpha['quality']['score']} | 综合{alpha['composite']['score']} → {alpha['composite']['signal']}")
    
    # Step 5: 相关性
    print("  [5/6] 相关性分析...")
    correlation = calc_correlation(klines, market)
    if correlation:
        print(f"  ✅ 年化波动{correlation.get('volatility_annual','?')}% | 最大回撤{correlation.get('max_drawdown_90d','?')}%")
    
    # Step 6: 资金流 + 资讯
    print("  [6/6] 资金流 + 资讯...")
    fund_flow = fetch_fund_flow(market, num)
    news = fetch_news(market, num, quote.get("name", ""))
    if news:
        print(f"  ✅ {news['total']}条新闻, 情绪分{news['sentiment']}")
    
    # 组装结果
    result = {
        "meta": {
            "code": code, "market": market_name, "api_code": api_code,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "quote": quote,
        "fundamentals": fundamentals or {},
        "tech": tech,
        "alpha_factors": alpha,
        "correlation": correlation,
        "fund_flow": fund_flow,
        "news": news,
    }
    
    # 计算PEG
    pe = fundamentals.get("pe_ttm", 0) if fundamentals else 0
    roe = fundamentals.get("roe", 10) if fundamentals else 10
    if pe and pe > 0 and roe > 0:
        est_growth = min(roe * 0.8, 40)
        peg = round(pe / est_growth, 2)
        result["peg"] = {
            "value": peg,
            "growth_assumption": round(est_growth, 1),
            "signal": "🟢 低估" if peg < 1 else ("🟡 合理" if peg < 1.5 else "🔴 偏高"),
            "color": "#3fb950" if peg < 1 else ("#d29922" if peg < 1.5 else "#f85149"),
        }
    
    # 计算均线偏离
    if ma5 and quote:
        result["ma_deviation"] = {
            "ma5": round((quote["price"] - ma5) / ma5 * 100, 1),
            "ma20": round((quote["price"] - ma20) / ma20 * 100, 1) if ma20 else None,
            "ma60": round((quote["price"] - ma60) / ma60 * 100, 1) if ma60 else None,
        }
    
    print(f"\n✅ 分析完成! 数据维度: {len(result)} 个模块")
    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python3 analyze.py <股票代码>")
        print("示例: python3 analyze.py 300750")
        print("      python3 analyze.py 00700")
        sys.exit(1)
    
    code = sys.argv[1]
    result = analyze(code)
    
    if result:
        out_dir = os.path.join(os.path.dirname(__file__), "stocks")
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, f"{code}.json")
        
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n📁 已保存: {out_file}")
        print(f"   文件大小: {os.path.getsize(out_file):,} bytes")
    else:
        print("\n❌ 分析失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
