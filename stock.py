import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import openai
import urllib.request
import urllib.parse
import json
import time
import requests
from bs4 import BeautifulSoup
import re

# ==========================================
# 1. 환경 설정 및 HTS 프로페셔널 테마 (CSS)
# ==========================================
st.set_page_config(page_title="Institutional Equity Research Terminal", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f1f5f9; }
    h1, h2, h3, h4, h5 { color: #0f172a; font-family: 'Malgun Gothic', sans-serif; font-weight: 700; }
    .section-card { background-color: #ffffff; padding: 24px; border-radius: 8px; border: 1px solid #cbd5e1; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05); margin-bottom: 24px; }
    .stButton>button { background-color: #1e293b; color: white; border-radius: 2px; border: none; font-weight: bold; border: 1px solid #334155; }
    .stButton>button:hover { background-color: #334155; color: white; }
    .trade-box { background-color: #f8fafc; padding: 15px; border: 1px solid #cbd5e1; margin-bottom: 10px; border-radius: 4px; }
    .bullish-box { background-color: #f0f7ff; border-left: 4px solid #2563eb; padding: 15px; margin-bottom: 10px; border-radius: 4px; }
    .bearish-box { background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; margin-bottom: 10px; border-radius: 4px; }
    .info-text { color: #475569; font-size: 0.9em; }
    .macro-ticker { background-color: #0f172a; color: #f8fafc; padding: 10px; border-radius: 4px; text-align: center; font-weight: bold; font-family: 'Courier New', Courier, monospace;}
    .positive-val { color: #ef4444; }
    .negative-val { color: #3b82f6; }
    .disclaimer { font-size: 0.8em; color: #6b7280; text-align: center; border-top: 1px solid #e5e7eb; padding-top: 20px; margin-top: 40px; }
    .news-item { padding: 8px 0; border-bottom: 1px dashed #cbd5e1; }
    .news-item:last-child { border-bottom: none; }
</style>
""", unsafe_allow_html=True)

NAVER_CLIENT_ID = st.secrets["NAVER_CLIENT_ID"]
NAVER_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
if OPENAI_API_KEY: openai.api_key = OPENAI_API_KEY

# ==========================================
# 2. 10개 섹터 & 대장주별 1:1 맞춤형 데이터베이스
# ==========================================
MARKET_THEMES = {
    "[01] 반도체 및 소부장 (Semiconductors)": {
        "macro": "[Macro Check] 글로벌 AI 서버 투자 집행률 및 선단 파운드리 가동률 지표 점검.",
        "leaders": {
            "삼성전자 (1위)": {
                "ticker": "005930.KS",
                "수혜주": [
                    {"name": "원익IPS", "ticker": "091700.KQ", "relation": "메인 증착장비 공급사", "action": "실적 턴어라운드", "horizon": "중장기", "entry_price": "30,000원", "price_merit": "설비투자 재개 수혜", "growth_point": "3나노 이하 장비 확대", "risk_factor": "업황 회복 지연"},
                    {"name": "동진쎄미켐", "ticker": "005290.KQ", "relation": "포토레지스트 국산화 파트너", "action": "안정적 성장", "horizon": "장기", "entry_price": "35,000원", "price_merit": "국산화 독점 지위", "growth_point": "EUV 라인 확대", "risk_factor": "원자재 마진 압박"}
                ]
            },
            "SK하이닉스 (2위)": {
                "ticker": "000660.KS",
                "수혜주": [
                    {"name": "한미반도체", "ticker": "042700.KS", "relation": "HBM TC본더 독점", "action": "실적 고성장", "horizon": "중기", "entry_price": "130,000원", "price_merit": "독점 프리미엄", "growth_point": "HBM 단가 상승", "risk_factor": "경쟁사 퀄 테스트"},
                    {"name": "테크윙", "ticker": "089030.KQ", "relation": "HBM 테스트 핸들러", "action": "수주 모멘텀", "horizon": "중기", "entry_price": "38,000원", "price_merit": "수율 향상 필수 장비", "growth_point": "독점 장비 가시화", "risk_factor": "검수 지연"}
                ]
            }
        }
    },
    "[02] 로봇 및 자동화 (Robotics)": {
        "macro": "[Macro Check] 인구 구조 변화 및 기업 CAPEX 자동화 설비 동향.",
        "leaders": {
            "두산로보틱스 (1위)": {
                "ticker": "454910.KS",
                "수혜주": [
                    {"name": "SPG", "ticker": "058610.KQ", "relation": "정밀 감속기 파트너", "action": "턴어라운드", "horizon": "중장기", "entry_price": "25,000원", "price_merit": "국산화 1위 프리미엄", "growth_point": "산업용 로봇 수요 개화", "risk_factor": "중국산 저가 공세"}
                ]
            },
            "레인보우로보틱스 (2위)": {
                "ticker": "277810.KQ",
                "수혜주": [
                    {"name": "엠로", "ticker": "058970.KQ", "relation": "삼성 밸류체인 연관 SCM 소프트웨어", "action": "안정적 우상향", "horizon": "장기", "entry_price": "60,000원", "price_merit": "AI 기반 공급망 관리 독점", "growth_point": "글로벌 SaaS 진출", "risk_factor": "초기 해외 마케팅 비용"}
                ]
            }
        }
    },
    "[03] 2차전지 및 소재 (EV Batteries)": {
        "macro": "[Macro Check] 리튬/니켈 가격 동향 및 북미 전기차 인도량 확인.",
        "leaders": {
            "LG에너지솔루션 (1위)": {
                "ticker": "373220.KS",
                "수혜주": [
                    {"name": "엔켐", "ticker": "348370.KQ", "relation": "북미 공장 핵심 전해액", "action": "모멘텀 보유", "horizon": "중기", "entry_price": "220,000원", "price_merit": "IRA 규제 수혜", "growth_point": "북미 캡티브 물량 확대", "risk_factor": "고객사 공급망 다변화"}
                ]
            },
            "삼성SDI (2위)": {
                "ticker": "006400.KS",
                "수혜주": [
                    {"name": "상신EDP", "ticker": "091580.KQ", "relation": "원통형 캔 부품 독점", "action": "안정적 성장", "horizon": "장기", "entry_price": "14,000원", "price_merit": "독점 구조 프리미엄", "growth_point": "4680 캔 양산", "risk_factor": "전동공구 수요 부진"}
                ]
            },
            "포스코홀딩스 (3위)": {
                "ticker": "005490.KS",
                "수혜주": [
                    {"name": "포스코퓨처엠", "ticker": "003670.KS", "relation": "그룹 양/음극재 핵심", "action": "모멘텀 보유", "horizon": "중장기", "entry_price": "250,000원", "price_merit": "원가 경쟁력", "growth_point": "글로벌 OEM 수주", "risk_factor": "캐즘 장기화"}
                ]
            }
        }
    },
    "[04] 모빌리티 및 전장 (Automotive)": {
        "macro": "[Macro Check] 글로벌 판매량 증감 및 원달러 환율 수출 마진 점검.",
        "leaders": {
            "현대차 (1위)": {
                "ticker": "005380.KS",
                "수혜주": [
                    {"name": "현대모비스", "ticker": "012330.KS", "relation": "모듈 및 전장 핵심", "action": "가치주 저평가", "horizon": "장기", "entry_price": "210,000원", "price_merit": "극단적 저평가 지속", "growth_point": "전동화 부품 흑자 전환", "risk_factor": "지배구조 개편 지연"},
                    {"name": "서연이화", "ticker": "200880.KS", "relation": "미국 신공장 동반 진출", "action": "저평가 국면", "horizon": "중기", "entry_price": "16,000원", "price_merit": "PER 3배 수준", "growth_point": "미국 공장 가동 매출 점프", "risk_factor": "플라스틱 가격 상승"}
                ]
            },
            "기아 (2위)": {
                "ticker": "000270.KS",
                "수혜주": [
                    {"name": "HL만도", "ticker": "204320.KS", "relation": "주요 차종 섀시/제동", "action": "모멘텀 회복", "horizon": "중기", "entry_price": "38,000원", "price_merit": "체질 개선 완료", "growth_point": "인도 로컬 공장 수주", "risk_factor": "원자재 전가 지연"}
                ]
            }
        }
    },
    "[05] 바이오 및 신약 (Bio & Pharma)": {
        "macro": "[Macro Check] 글로벌 금리 및 주요 파이프라인 FDA 승인 데이터 공시.",
        "leaders": {
            "삼성바이오로직스 (1위)": {
                "ticker": "207940.KS",
                "수혜주": [
                    {"name": "바이넥스", "ticker": "053030.KQ", "relation": "중소형 위탁생산(CDMO) 대안", "action": "실적 개선", "horizon": "중기", "entry_price": "11,000원", "price_merit": "생물보안법 반사이익", "growth_point": "미국/유럽 고객사 다변화", "risk_factor": "바이오 벤처 펀딩 위축"}
                ]
            },
            "유한양행 (2위)": {
                "ticker": "000100.KS",
                "수혜주": [
                    {"name": "오스코텍", "ticker": "039200.KQ", "relation": "렉라자 원개발사", "action": "모멘텀 가시화", "horizon": "장기", "entry_price": "30,000원", "price_merit": "로열티 유입 가치", "growth_point": "글로벌 마일스톤 반영", "risk_factor": "후속 파이프라인 부재"}
                ]
            },
            "알테오젠 (3위)": {
                "ticker": "196170.KQ",
                "수혜주": [
                    {"name": "리가켐바이오", "ticker": "141080.KQ", "relation": "ADC 기술수출 파트너격", "action": "성장 기대", "horizon": "중장기", "entry_price": "90,000원", "price_merit": "밸류 하단 지지", "growth_point": "ADC 트렌드 선도", "risk_factor": "임상 초기 독성 이슈"}
                ]
            }
        }
    },
    "[06] 방위산업 (Defense & Aerospace)": {
        "macro": "[Macro Check] 중동/유럽 지정학적 긴장도 및 무기 수출 금융 잔액.",
        "leaders": {
            "한화에어로스페이스 (1위)": {
                "ticker": "012450.KS",
                "수혜주": [
                    {"name": "한화시스템", "ticker": "272210.KS", "relation": "방산 전자/위성 계열사", "action": "모멘텀 보유", "horizon": "중장기", "entry_price": "18,000원", "price_merit": "체계 업체 대비 주가 탄력성", "growth_point": "무기 전장화 수혜", "risk_factor": "우주 신사업 R&D 비용"}
                ]
            },
            "LIG넥스원 (2위)": {
                "ticker": "079550.KS",
                "수혜주": [
                    {"name": "아이쓰리시스템", "ticker": "214430.KQ", "relation": "유도무기 적외선 영상센서 독점", "action": "가치주 성격", "horizon": "장기", "entry_price": "35,000원", "price_merit": "군수용 센서 독점 체제", "growth_point": "천궁 수출 물량 탑재", "risk_factor": "내수 방산 예산 감축"}
                ]
            },
            "현대로템 (3위)": {
                "ticker": "064350.KS",
                "수혜주": [
                    {"name": "SNT다이내믹스", "ticker": "003570.KS", "relation": "K2 전차 변속기 국산화", "action": "실적 턴어라운드", "horizon": "중기", "entry_price": "16,000원", "price_merit": "국산 변속기 채택 마진 개선", "growth_point": "폴란드/튀르키예 추가 수출", "risk_factor": "수출 계약 지연"}
                ]
            }
        }
    },
    "[07] 전력 인프라 (Power & Energy)": {
        "macro": "[Macro Check] 노후 전력망 교체 예산 및 데이터센터 전력 소비량 확인.",
        "leaders": {
            "HD현대일렉트릭 (1위)": {
                "ticker": "267260.KS",
                "수혜주": [
                    {"name": "일진전기", "ticker": "103590.KS", "relation": "초고압 변압기/전선 턴키 경쟁력", "action": "성장 가속", "horizon": "중장기", "entry_price": "22,000원", "price_merit": "수주 잔고 대비 저평가", "growth_point": "미국 초고압망 교체 수주", "risk_factor": "유상증자 등 희석 우려"}
                ]
            },
            "LS일렉트릭 (2위)": {
                "ticker": "010120.KS",
                "수혜주": [
                    {"name": "제룡전기", "ticker": "033100.KQ", "relation": "주상/소형 변압기 수출 대장", "action": "수익성 극대화", "horizon": "중기", "entry_price": "65,000원", "price_merit": "이익률 30% 이상 유지", "growth_point": "미국 배전망 교체 폭증", "risk_factor": "미국 현지 관세 부과"}
                ]
            }
        }
    },
    "[08] 조선 및 기자재 (Shipbuilding)": {
        "macro": "[Macro Check] 신조선가(클락슨 지수) 상승세 및 글로벌 선박 규제.",
        "leaders": {
            "HD한국조선해양 (1위)": {
                "ticker": "009540.KS",
                "수혜주": [
                    {"name": "HD현대미포", "ticker": "010620.KS", "relation": "중형 PC선 핵심 계열사", "action": "턴어라운드", "horizon": "중기", "entry_price": "85,000원", "price_merit": "적자 탈출 기대감", "growth_point": "친환경 선박 발주 사이클", "risk_factor": "인력난 지속"}
                ]
            },
            "한화오션 (2위)": {
                "ticker": "042660.KS",
                "수혜주": [
                    {"name": "한화엔진", "ticker": "082740.KS", "relation": "대형 선박 엔진 수직계열화", "action": "이익률 개선", "horizon": "중장기", "entry_price": "11,000원", "price_merit": "시너지 편입 가치", "growth_point": "이중연료 엔진 채택 확대", "risk_factor": "타사 물량 이탈"}
                ]
            },
            "삼성중공업 (3위)": {
                "ticker": "010140.KS",
                "수혜주": [
                    {"name": "성광벤드", "ticker": "014620.KQ", "relation": "해양플랜트/LNG 피팅 부품", "action": "가치주", "horizon": "중기", "entry_price": "13,000원", "price_merit": "무차입 현금 경영", "growth_point": "LNG 인프라 투자 지속", "risk_factor": "유가 급락 시 발주 취소"}
                ]
            }
        }
    },
    "[09] IT 플랫폼 (Tech & SW)": {
        "macro": "[Macro Check] B2B IT 예산 증감률 및 AI LLM 상용화/수익화 현황.",
        "leaders": {
            "NAVER (1위)": {
                "ticker": "035420.KS",
                "수혜주": [
                    {"name": "플레이디", "ticker": "237820.KQ", "relation": "네이버 검색광고 대행 파트너", "action": "실적 방어", "horizon": "단기", "entry_price": "6,000원", "price_merit": "현금 창출 대비 저평가", "growth_point": "디지털 마케팅 단가 인상", "risk_factor": "광고 경기 침체"}
                ]
            },
            "카카오 (2위)": {
                "ticker": "035720.KS",
                "수혜주": [
                    {"name": "디어유", "ticker": "376300.KQ", "relation": "카카오/SM 엔터 밸류체인 소통 플랫폼", "action": "저평가", "horizon": "중기", "entry_price": "28,000원", "price_merit": "구독 레버리지 효과", "growth_point": "일본/중국 아티스트 입점", "risk_factor": "팬덤 이탈 우려"}
                ]
            },
            "삼성SDS (3위)": {
                "ticker": "018260.KS",
                "수혜주": [
                    {"name": "엠로", "ticker": "058970.KQ", "relation": "자회사격 SCM 소프트웨어 파트너", "action": "성장 가시화", "horizon": "장기", "entry_price": "60,000원", "price_merit": "B2B SaaS 락인 효과", "growth_point": "SDS 연계 글로벌 진출", "risk_factor": "밸류에이션 부담"}
                ]
            }
        }
    },
    "[10] 금융 지주 (Finance & Value-up)": {
        "macro": "[Macro Check] 기준금리 동향(NIM 연동) 및 밸류업 가이드라인 이행 점검.",
        "leaders": {
            "KB금융 (1위)": {
                "ticker": "055560.KS",
                "수혜주": [
                    {"name": "JB금융지주", "ticker": "175330.KS", "relation": "고수익성 지방은행 가치주 대안", "action": "초고배당", "horizon": "장기", "entry_price": "12,000원", "price_merit": "가장 높은 ROE 보유", "growth_point": "자사주 매입 및 소각 확대", "risk_factor": "PF 대손충당금 반영"}
                ]
            },
            "메리츠금융지주 (2위)": {
                "ticker": "138040.KS",
                "수혜주": [
                    {"name": "키움증권", "ticker": "039490.KS", "relation": "밸류업 브로커리지 대안 증권사", "action": "실적 성장", "horizon": "중기", "entry_price": "120,000원", "price_merit": "지주사 대비 상대적 저평가", "growth_point": "적극적 주주환원 정책", "risk_factor": "거래대금 감소"}
                ]
            },
            "신한지주 (3위)": {
                "ticker": "055550.KS",
                "수혜주": [
                    {"name": "우리금융지주", "ticker": "316140.KS", "relation": "전통 시중은행 고배당 대안", "action": "배당 매력", "horizon": "장기", "entry_price": "14,000원", "price_merit": "7% 이상 배당률", "growth_point": "증권사 인수를 통한 다변화", "risk_factor": "자본비율 열위"}
                ]
            }
        }
    }
}

# ==========================================
# 3. 데이터 로딩 및 API 통신 
# ==========================================
@st.cache_data(ttl=1800)
def get_macro_data():
    symbols = {"KOSPI": "^KS11", "KOSDAQ": "^KQ11", "S&P 500": "^GSPC", "USD/KRW": "KRW=X"}
    macro_info = {}
    for name, sym in symbols.items():
        try:
            hist = yf.Ticker(sym).history(period="5d")
            if len(hist) >= 2:
                cur = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                diff = cur - prev
                pct = (diff / prev) * 100
                macro_info[name] = {"price": cur, "diff": diff, "pct": pct}
        except:
            macro_info[name] = {"price": 0, "diff": 0, "pct": 0}
    return macro_info

def get_finance_url(ticker: str) -> str:
    if ".KS" in ticker or ".KQ" in ticker:
        code = ticker.split('.')[0]
        return f"https://finance.naver.com/item/main.naver?code={code}"
    return f"https://finance.yahoo.com/quote/{ticker}"

@st.cache_data(ttl=1800)
def get_quick_price(ticker):
    try: return yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
    except: return 0

@st.cache_data(ttl=1800)
def get_stock_financials(ticker):
    try:
        info = yf.Ticker(ticker).info
        return {
            "marketCap": info.get('marketCap', 0),
            "trailingPE": info.get('trailingPE', 'N/A'),
            "priceToBook": info.get('priceToBook', 'N/A'),
            "fiftyTwoWeekHigh": info.get('fiftyTwoWeekHigh', 'N/A'),
            "fiftyTwoWeekLow": info.get('fiftyTwoWeekLow', 'N/A')
        }
    except: return {}

@st.cache_data(ttl=3600)
def get_real_target_price(ticker):
    if ".KS" not in ticker and ".KQ" not in ticker: return "해외주식 (지원불가)"
    code = ticker.split('.')[0]
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        target_th = soup.find("th", string="목표주가")
        if target_th:
            target_td = target_th.find_next_sibling("td")
            if target_td and target_td.find("em"):
                price_text = target_td.find("em").text.strip()
                if price_text and price_text != "N/A": return f"{price_text} 원"
        return "컨센서스 없음"
    except: return "조회 지연"

@st.cache_data(ttl=1800)
def get_recent_news(name, display_count=3):
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET: return []
    encText = urllib.parse.quote(f"{name} 주식")
    url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display={display_count}&sort=sim"
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
    req.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode('utf-8'))
            return [{"title": i['title'].replace('<b>','').replace('</b>',''), "url": i['link']} for i in data['items']]
    except: return []

@st.cache_data(ttl=1800)
def generate_ai_report_parsed(ticker_name, price, news_list):
    if not OPENAI_API_KEY:
        time.sleep(1)
        return 50, f"[{ticker_name}] 실적 개선 기대감 및 저평가 매력 부각", "[리스크] 전방 산업 수요 둔화 등 변동성 주의"
    
    titles = [n['title'] for n in news_list]
    prompt = f"""
    분석 대상: {ticker_name}({price}원). 뉴스({', '.join(titles)})를 바탕으로 분석.
    반드시 아래 형식 지킬 것.
    
    [SCORE]0부터 100사이 숫자[/SCORE]
    [BULLISH]상승 모멘텀/호재 3줄 요약[/BULLISH]
    [BEARISH]하락 리스크/악재 3줄 요약[/BEARISH]
    """
    try:
        response = openai.ChatCompletion.create(model="gpt-4", messages=[{"role": "system", "content": prompt}], temperature=0.1)
        text = response.choices[0].message.content
        
        score_match = re.search(r'\[SCORE\](\d+)\[/SCORE\]', text)
        bullish_match = re.search(r'\[BULLISH\](.*?)\[/BULLISH\]', text, re.DOTALL)
        bearish_match = re.search(r'\[BEARISH\](.*?)\[/BEARISH\]', text, re.DOTALL)
        
        score = int(score_match.group(1)) if score_match else 50
        bullish = bullish_match.group(1).strip() if bullish_match else "데이터 요약 실패"
        bearish = bearish_match.group(1).strip() if bearish_match else "데이터 요약 실패"
        return score, bullish, bearish
    except Exception as e: return 50, "통신 지연", f"에러: {e}"

def draw_professional_chart(df):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.75, 0.25])
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], 
                                 name='Price', increasing_line_color='#ef4444', decreasing_line_color='#3b82f6'), row=1, col=1)
    
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#f59e0b', width=1.5), name='20 MA'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='#10b981', width=1.5), name='60 MA'), row=1, col=1)
    
    colors = ['#ef4444' if row['Close'] >= row['Open'] else '#3b82f6' for _, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)
    
    fig.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10), height=550, showlegend=False, plot_bgcolor='#ffffff', paper_bgcolor='#ffffff')
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#f1f5f9')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f1f5f9')
    return fig

def draw_gauge(score):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "AI Score", 'font': {'size': 14, 'color': '#334155'}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#cbd5e1"},
            'bar': {'color': "#1e293b"},
            'steps' : [
                {'range': [0, 40], 'color': "#fee2e2"},
                {'range': [40, 60], 'color': "#f1f5f9"},
                {'range': [60, 100], 'color': "#dbeafe"}],
        }
    ))
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=30, b=10))
    return fig

# ==========================================
# 4. 프론트엔드 UI 
# ==========================================
def main():
    st.sidebar.markdown("### [ 시스템 설정 ]")
    news_count = st.sidebar.slider("[ 표시할 뉴스 개수 ]", min_value=3, max_value=10, value=3, step=1)
    st.sidebar.markdown("---")

    macro_data = get_macro_data()
    if macro_data:
        cols = st.columns(4)
        for idx, (name, data) in enumerate(macro_data.items()):
            color_class = "positive-val" if data['diff'] >= 0 else "negative-val"
            sign = "+" if data['diff'] >= 0 else ""
            html = f"<div class='macro-ticker'>{name} : {data['price']:,.2f} <span class='{color_class}'>({sign}{data['pct']:.2f}%)</span></div>"
            cols[idx].markdown(html, unsafe_allow_html=True)
            
    st.markdown("<br>", unsafe_allow_html=True)
    st.title("Institutional Equity Research Terminal")
    
    st.markdown("### [ 나의 관심 종목 실시간 속보 ]")
    with st.container(border=True):
        col_w1, col_w2 = st.columns([8, 2])
        with col_w1:
            my_stock = st.text_input("모니터링 대상 종목 입력 :", value="삼성전자")
        with col_w2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("[ 뉴스 새로고침 ]", use_container_width=True):
                get_recent_news.clear()
                st.rerun()
        
        if my_stock:
            with st.spinner(f"'{my_stock}' 관련 데이터 수집 중..."):
                my_news = get_recent_news(my_stock, news_count)
                if my_news:
                    for n in my_news:
                        st.markdown(f"<div class='news-item'>- <strong>[{my_stock}]</strong> <a href='{n['url']}' target='_blank' style='color:#1e40af; text-decoration:none;'>{n['title']}</a></div>", unsafe_allow_html=True)
                else:
                    st.info("현재 수집된 관련 속보가 없습니다.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    theme = st.sidebar.selectbox("[ Sector Select ]", list(MARKET_THEMES.keys()))
    leader_name = st.sidebar.selectbox("[ Sector Leader Select ]", list(MARKET_THEMES[theme]["leaders"].keys()))
    
    leader_data = MARKET_THEMES[theme]["leaders"][leader_name]
    leader_ticker = leader_data["ticker"]
    custom_suhyeju_list = leader_data["수혜주"]
    
    st.markdown("### 1. Sector Macro Analysis")
    with st.container(border=True):
        st.markdown(f"#### {theme.split(' ')[1]} Macro Indicator")
        st.info(MARKET_THEMES[theme]["macro"])

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### 2. Sector Leader Research")
    with st.container(border=True):
        st.subheader(f"[Sector Leader] {leader_name.split(' ')[0]}")
        
        if st.button(f"[{leader_name.split(' ')[0]}] 차트 및 리서치 실행", use_container_width=True):
            with st.spinner("마켓 데이터 로딩 중..."):
                df = yf.Ticker(leader_ticker).history(period="6mo")
                if not df.empty:
                    current_price = df['Close'].iloc[-1]
                    st.metric("실시간 체결가", f"{current_price:,.0f} KRW")
                    
                    st.plotly_chart(draw_professional_chart(df), use_container_width=True)
                    
                    tab1, tab2 = st.tabs(["[ AI 팩트 체크 ]", "[ 시장 공시 및 뉴스 ]"])
                    news = get_recent_news(leader_name.split(' ')[0], news_count)
                    
                    with tab1:
                        score, bullish, bearish = generate_ai_report_parsed(leader_name.split(' ')[0], current_price, news)
                        
                        c1, c2 = st.columns([1.5, 5.5])
                        with c1: st.plotly_chart(draw_gauge(score), use_container_width=True)
                        with c2:
                            st.markdown(f"<div class='bullish-box'><strong>[ 긍정적 모멘텀 ]</strong><br>{bullish}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div class='bearish-box'><strong>[ 부정적 리스크 ]</strong><br>{bearish}</div>", unsafe_allow_html=True)
                            
                        report_text = f"분석 기업: {leader_name.split(' ')[0]}\n현재가: {current_price:,.0f}원\n투심 점수: {score}점\n\n[긍정적 팩트]\n{bullish}\n\n[부정적 팩트]\n{bearish}"
                        st.download_button("[ 리포트 텍스트 다운로드 ]", data=report_text, file_name=f"{leader_name.split(' ')[0]}_AI_Report.txt", mime="text/plain")
                            
                    with tab2:
                        for n in news: st.markdown(f"- **[{n['title']}]({n['url']})**")
                else:
                    st.error("데이터 통신 지연. 종목 코드를 확인하십시오.")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"### 3. Value Chain Partners ({leader_name.split(' ')[0]} 핵심 공급망)")
    st.caption(f"{leader_name.split(' ')[0]}와 직접적인 거래 및 수혜 관계가 있는 파트너사 목록입니다.")
    
    with st.container(border=True):
        for idx, su in enumerate(custom_suhyeju_list):
            toggle_key = f"toggle_{su['ticker']}"
            if toggle_key not in st.session_state:
                st.session_state[toggle_key] = False
                
            col1, col2 = st.columns([6, 2])
            with col1: st.markdown(f"#### {su['name']} <span class='info-text'>({su['relation']})</span>", unsafe_allow_html=True)
            with col2: 
                if st.button("[ 상세 리서치 토글 ]", key=f"btn_{su['ticker']}", use_container_width=True):
                    st.session_state[toggle_key] = not st.session_state[toggle_key]

            if st.session_state[toggle_key]:
                with st.container():
                    sc1, sc2 = st.columns([2.5, 4.5])
                    
                    with sc1:
                        su_price = get_quick_price(su['ticker'])
                        real_target_price = get_real_target_price(su['ticker'])
                        
                        st.markdown(f"""
                        <div class='trade-box'>
                            <h5 style='margin-top:0px; margin-bottom:5px;'>상태: {su['action']}</h5>
                            <div style='font-size:1.1em; font-weight:bold; margin-bottom:10px;'>현재가: {su_price:,.0f} KRW</div>
                            <hr style='margin: 10px 0;'>
                            <div class='info-text' style='line-height: 1.6;'>
                                <b>[투자기간]</b> {su['horizon']}<br>
                                <b>[진입타점]</b> {su['entry_price']}<br>
                                <b>[목표가(컨센서스)]</b> <span style='color:#dc2626; font-weight:bold;'>{real_target_price}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.link_button("[ 매매 호가창 이동 ]", get_finance_url(su['ticker']), use_container_width=True)
                        
                    with sc2:
                        st.markdown("**[ 팩트 기반 투자 포인트 ]**")
                        st.write(f"- **가치 지표:** {su['price_merit']}")
                        st.write(f"- **성장 지표:** {su['growth_point']}")
                        st.write(f"- **위험 지표:** {su['risk_factor']}")
                        
                        f_info = get_stock_financials(su['ticker'])
                        if f_info:
                            mcap = f_info['marketCap'] / 1000000000000 if f_info['marketCap'] else 0
                            st.markdown(f"<div class='trade-box info-text'><b>[ 실시간 재무 스냅샷 ]</b> 시가총액: {mcap:.1f}조 원 | PER: {f_info['trailingPE']} | PBR: {f_info['priceToBook']} | 52주 고가: {f_info['fiftyTwoWeekHigh']} | 52주 저가: {f_info['fiftyTwoWeekLow']}</div>", unsafe_allow_html=True)

                    su_ai_key = f"ai_report_{su['ticker']}"
                    if st.button(f"[{su['name']}] 실시간 AI 투자 심리 분석", key=f"run_ai_{su['ticker']}"):
                        st.session_state[su_ai_key] = True

                    if st.session_state.get(su_ai_key, False):
                        with st.spinner("마켓 데이터 파싱 중..."):
                            su_news = get_recent_news(su['name'], news_count)
                            score, bullish, bearish = generate_ai_report_parsed(su['name'], su_price, su_news)
                            
                            ac1, ac2 = st.columns([2, 5])
                            with ac1: st.plotly_chart(draw_gauge(score), use_container_width=True, key=f"gauge_{su['ticker']}")
                            
                            with ac2:
                                st.markdown(f"<div class='bullish-box'><strong>[ 긍정적 모멘텀 ]</strong><br>{bullish}</div>", unsafe_allow_html=True)
                                st.markdown(f"<div class='bearish-box'><strong>[ 부정적 리스크 ]</strong><br>{bearish}</div>", unsafe_allow_html=True)
            
            if idx < len(custom_suhyeju_list) - 1:
                st.divider()

    st.markdown("""
    <div class='disclaimer'>
    <b>[ 투자 유의사항 및 면책 조항 ]</b><br>
    본 단말기에서 제공하는 데이터와 AI 분석 자료는 투자를 위한 <b>객관적 참고 자료</b>입니다.<br>
    특정 주식의 매수나 매도를 지시하지 않으며, 최종적인 투자 결정과 그에 따른 모든 책임은 전적으로 투자자 본인에게 있습니다.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()