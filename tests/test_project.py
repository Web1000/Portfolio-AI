"""Offline regression tests for calculations, integrations, and API contracts."""
import io
import json
import os
import unittest
from unittest.mock import patch

from app import create_app
from src.agents.news import classify, NewsAgent
from src.agents.technical import TechnicalAgent
from src.agents.value import calculate, ValueAgent, BusinessReport
from src.core.llm import structured, ModelResponseError
from src.core.signals import compute_rsi, compute_signals, compute_volume_signal, compute_volatility
from src.data_access.demo import fundamentals, prices
from src.data_access.market_data import fetch_ohlcv, get_market_snapshot, normalize_ticker, _guess_ticker
from src.data_access.sec_edgar import annual_fact, extract_financials, fetch_fundamentals


def facts_with(records):
    return {"facts": {"us-gaap": {key: {"units": {unit: values}} for key, (unit, values) in records.items()}}}


def annual(value, end="2025-12-31", start="2025-01-01", filed="2026-02-01"):
    return {"val": value, "start": start, "end": end, "filed": filed, "form": "10-K"}


class Calculations(unittest.TestCase):
    def test_value_is_per_share(self):
        result = calculate(fundamentals())
        self.assertEqual(result["value_per_share"], 120)
        self.assertAlmostEqual(result["margin_of_safety"], .2)
        self.assertEqual(result["owner_earnings_proxy"], 6e9)

    def test_negative_earnings_has_no_positive_valuation(self):
        result = calculate({**fundamentals(), "capex": 10e9})
        self.assertIsNone(result["value_per_share"])
        self.assertIsNone(result["margin_of_safety"])
        self.assertEqual(result["cash_flow_score"], 0)

    def test_missing_debt_is_not_debt_free(self):
        result = calculate({**fundamentals(), "debt": None})
        self.assertIsNone(result["debt_score"])
        self.assertIsNone(result["debt_to_earnings"])

    def test_zero_debt_is_valid(self):
        self.assertEqual(calculate({**fundamentals(), "debt": 0})["debt_score"], 15)

    def test_missing_capex_is_not_zero(self):
        self.assertIsNone(calculate({**fundamentals(), "capex": None})["owner_earnings_proxy"])

    def test_missing_shares_or_price(self):
        for key in ("shares", "current_price"):
            for value in (None, 0):
                with self.subTest(key=key, value=value):
                    self.assertIsNone(calculate({**fundamentals(), key: value})["margin_of_safety"])

    def test_flat_rsi_is_neutral(self):
        self.assertEqual(compute_rsi([10]*30), 50)

    def test_declining_rsi_is_zero_and_weak(self):
        data = prices(); data["closes"] = list(range(200, 80, -1))
        result = compute_signals(data)
        self.assertEqual(result["momentum"]["rsi"], 0)
        self.assertEqual(result["momentum"]["signal"], "weak")

    def test_zero_volume(self):
        self.assertEqual(compute_volume_signal([10]*19+[0])["signal"], "low")
        self.assertEqual(compute_volume_signal([0]*20)["signal"], "unknown")

    def test_short_history_is_not_bearish(self):
        data = {k: v[:15] if isinstance(v, list) else v for k, v in prices().items()}
        self.assertEqual(compute_signals(data)["trend"]["signal"], "unknown")

    def test_return_spans_21_intervals(self):
        data = prices(); data["closes"] = list(range(1,121))
        self.assertAlmostEqual(compute_signals(data)["momentum"]["one_month_return"], round((120/99-1)*100,2))

    def test_invalid_prices_and_misaligned_arrays(self):
        for value in (0, -1, float("nan"), float("inf")):
            data=prices();data["closes"][0]=value
            with self.assertRaises(ValueError): compute_signals(data)
        data=prices();data["opens"].pop()
        with self.assertRaises(ValueError): compute_signals(data)

    def test_flat_volatility(self):
        self.assertEqual(compute_volatility([10]*30), 0)


class SECFacts(unittest.TestCase):
    def test_new_period_beats_late_old_filing_and_quarter(self):
        facts=facts_with({"Cash":("USD", [annual(100), annual(20,start="2025-10-01"), annual(90,end="2024-12-31",start="2024-01-01",filed="2026-03-01")])})
        self.assertEqual(annual_fact(facts,["Cash"],"USD",duration=True)["val"],100)

    def test_latest_amendment_wins(self):
        a=annual(120,filed="2026-03-01");a["form"]="10-K/A"
        facts=facts_with({"Cash":("USD",[annual(100),a])})
        self.assertEqual(annual_fact(facts,["Cash"],"USD",duration=True)["val"],120)

    def test_missing_facts_and_wrong_unit(self):
        facts=facts_with({"Cash":("shares",[annual(100)])})
        self.assertIsNone(annual_fact(facts,["Cash"],"USD"))

    def test_period_alignment(self):
        facts=facts_with({"NetCashProvidedByUsedInOperatingActivities":("USD",[annual(100)]),
                          "PaymentsToAcquirePropertyPlantAndEquipment":("USD",[annual(20,end="2024-12-31",start="2024-01-01")])})
        result=extract_financials(facts)
        self.assertIsNone(result["capex"])
        self.assertIsNone(result["debt"])

    def test_debt_components(self):
        facts=facts_with({"NetCashProvidedByUsedInOperatingActivities":("USD",[annual(100)]),
                          "LongTermDebtCurrent":("USD",[annual(10)]), "LongTermDebtNoncurrent":("USD",[annual(30)]),
                          "ShortTermBorrowings":("USD",[annual(5)])})
        self.assertEqual(extract_financials(facts)["debt"],45)

    def test_missing_cash_flow_fails(self):
        with self.assertRaises(ValueError): extract_financials({})

    @patch('src.data_access.sec_edgar._get_json')
    def test_live_provider_parses_mocked_responses(self, get):
        facts=facts_with({"NetCashProvidedByUsedInOperatingActivities":("USD",[annual(100)])})
        get.side_effect=[{"0":{"ticker":"AAPL","cik_str":320193,"title":"Apple"}}, {"name":"Apple"}, facts,
                         {"chart":{"result":[{"meta":{"currency":"USD"},"timestamp":[1700000000],"indicators":{"quote":[{"close":[100]}]}}]}}]
        data=fetch_fundamentals("AAPL")
        self.assertEqual(data["current_price"],100)
        self.assertEqual(len(data["sources"]),2)


class Providers(unittest.TestCase):
    @patch('urllib.request.urlopen')
    def test_ohlcv_parsing_preserves_precision(self, fetch):
        data=prices(); quote={key:list(data[plural]) for key,plural in [('open','opens'),('high','highs'),('low','lows'),('close','closes'),('volume','volumes')]}
        quote['close'][0]=.00012
        payload={'chart':{'result':[{'timestamp':data['timestamps'],'indicators':{'quote':[quote]}}]}}
        fetch.return_value=io.StringIO(json.dumps(payload))
        self.assertEqual(fetch_ohlcv('AAPL')['closes'][0],.00012)

    @patch('urllib.request.urlopen')
    def test_empty_yahoo_response(self, fetch):
        fetch.side_effect=lambda *args,**kwargs:io.StringIO('{"chart":{"result":null}}')
        self.assertIsNone(fetch_ohlcv('AAPL'))
        self.assertIsNone(get_market_snapshot('AAPL price','stock'))

    def test_ticker_validation(self):
        self.assertEqual(normalize_ticker(' apple '),'AAPL')
        with self.assertRaises(ValueError): normalize_ticker('../../etc')

    def test_router_uses_word_boundaries(self):
        self.assertEqual(classify('What is the best method?'),'beginner')
        self.assertEqual(classify('ETH price'),'crypto')
        self.assertEqual(classify('Explain ETFs'),'etf')
        self.assertIsNone(_guess_ticker('metaphor','stock'))
        self.assertIsNone(_guess_ticker('What is an ETF?','etf'))

    @patch('src.core.llm.generate',return_value='{"business_score":99}')
    def test_invalid_model_schema(self, generate):
        with self.assertRaises(ModelResponseError): structured('test',BusinessReport)

    @patch('src.core.llm.generate',return_value='```json\n{"business_summary":"Example","moat_analysis":"Limited","business_score":1,"moat_score":0}\n```')
    def test_fenced_model_json(self, generate):
        self.assertEqual(structured('test',BusinessReport)['business_score'],1)


class API(unittest.TestCase):
    def setUp(self):
        self.app=create_app({'TESTING':True,'DEMO_MODE':True})
        self.client=self.app.test_client()

    def test_all_demo_workflows_are_network_free(self):
        with patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')), patch('src.core.llm.generate',side_effect=AssertionError('Model forbidden')):
            for workflow in ('value','technical','news'):
                with self.subTest(workflow=workflow):
                    response=self.client.post('/api/'+workflow,json={'ticker':'DEMO','question':'What is an ETF?'})
                    self.assertEqual(response.status_code,200)
                    self.assertEqual(response.json['mode'],'demo')
                    self.assertTrue(response.json['trace'])
                    json.dumps(response.json,allow_nan=False)


    def test_restored_module_pages_keep_navigation_and_demo_mode(self):
        for path in ('/', '/class2', '/class3', '/class4'):
            with self.subTest(path=path):
                response=self.client.get(path)
                self.assertEqual(response.status_code,200)
                self.assertIn(b'Offline demo',response.data)
                for route in (b'href="/class2"',b'href="/class3"',b'href="/class4"'):
                    self.assertIn(route,response.data)

    def test_all_page_assets_are_local_and_available(self):
        from html.parser import HTMLParser
        class Assets(HTMLParser):
            def __init__(self):
                super().__init__(); self.urls=[]
            def handle_starttag(self,tag,attrs):
                attrs=dict(attrs)
                if tag in ('script','img') and attrs.get('src'):
                    self.urls.append(attrs['src'])
                if tag=='link' and attrs.get('href'):
                    self.urls.append(attrs['href'])
        for path in ('/', '/class2', '/class3', '/class4'):
            parser=Assets();parser.feed(self.client.get(path).text)
            for url in parser.urls:
                with self.subTest(path=path,url=url):
                    self.assertTrue(url.startswith('/static/'))
                    with self.client.get(url) as response:
                        self.assertEqual(response.status_code,200)

    def test_live_templates_allow_real_inputs(self):
        client=create_app({'TESTING':True,'DEMO_MODE':False}).test_client()
        for path in ('/class2','/class3','/class4'):
            with self.subTest(path=path):
                page=client.get(path).text
                self.assertIn('Live research',page)
                self.assertNotIn('readonly',page)
                self.assertNotIn('Upgrade to Pro',page)

    def test_malformed_input(self):
        for payload in ([],None,{'ticker':3},{'ticker':''},{'ticker':'A'*100}):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post('/api/value',json=payload).status_code,400)

    def test_demo_cannot_mislabel_real_ticker(self):
        self.assertEqual(self.client.post('/api/value',json={'ticker':'AAPL'}).status_code,400)

    def test_unknown_workflow(self):
        self.assertEqual(self.client.post('/api/missing',json={}).status_code,404)

    def test_body_limit(self):
        self.assertEqual(self.client.post('/api/news',json={'question':'a'*20000}).status_code,413)

    def test_page_and_headers(self):
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertIn(b'Offline demo',response.data)
        self.assertIn("script-src 'self'",response.headers['Content-Security-Policy'])
        self.assertFalse(self.app.debug)

    @patch.dict(os.environ,{'ANTHROPIC_API_KEY':''})
    def test_live_requires_key(self):
        client=create_app({'TESTING':True,'DEMO_MODE':False}).test_client()
        self.assertEqual(client.post('/api/value',json={'ticker':'AAPL'}).status_code,503)

    @patch('src.agents.value.ValueAgent.run',side_effect=RuntimeError('private provider detail'))
    def test_upstream_error_is_sanitized(self, run):
        with self.assertLogs('app',level='ERROR'):
            response=self.client.post('/api/value',json={'ticker':'DEMO'})
        self.assertEqual(response.status_code,502)
        self.assertNotIn(b'private provider detail',response.data)

    @patch('src.agents.value.structured',return_value={'business_summary':'Limited profile','moat_analysis':'No evidence','business_score':1,'moat_score':0})
    @patch('src.agents.value.fetch_fundamentals',return_value={**fundamentals(),'debt':None})
    def test_incomplete_report_has_no_total(self, fetch, model):
        result=ValueAgent(demo=False).run('AAPL')
        self.assertIsNone(result['report']['score'])
        self.assertEqual(result['report']['assessment'],'Incomplete data')

    @patch('src.agents.technical.structured',return_value={'verdict':'mixed','summary':'Mixed','caution':'Limited','watch_next':'Trend'})
    @patch('src.agents.technical.fetch_ohlcv',side_effect=prices)
    def test_live_technical_graph_with_stubbed_services(self, fetch, model):
        fetch.side_effect=lambda ticker:prices()
        self.assertEqual(len(TechnicalAgent(False).run('AAPL')['trace']),3)

    @patch('src.agents.news.generate',side_effect=['Draft','Plain answer'])
    @patch('src.agents.news.get_news',return_value=[])
    @patch('src.agents.news.get_market_snapshot',return_value=None)
    def test_live_news_graph_with_no_evidence(self, snapshot, news, model):
        result=NewsAgent(False).run('What is diversification?')
        self.assertEqual(result['answer'],'Plain answer')
        self.assertIn('No external evidence',result['context'])


if __name__ == '__main__':
    unittest.main()
