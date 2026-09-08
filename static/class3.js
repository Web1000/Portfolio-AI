/* Original candlestick chart and overlays, connected to the corrected API. */
(() => {
'use strict';
const {$,demo,fmt,text,status,request,sources,download,trace} = PA;
let chart, resizeObserver, candleSeries, volumeSeries, ma20Series, ma50Series;
let loading = false;
function tsToDate(timestamp) { return new Date(timestamp * 1000).toISOString().slice(0,10); }
function renderChart(priceData, ta) {
  var container = document.getElementById("chart-container");
  var placeholder = document.getElementById("chart-placeholder");
  if (placeholder) placeholder.hidden = true;

  // Clear previous chart
  if (chart) chart.remove();
  if (resizeObserver) resizeObserver.disconnect();
  container.replaceChildren();

  chart = LightweightCharts.createChart(container, {
    width: container.clientWidth,
    height: 480,
    layout: {
      background: { color: "#111827" },
      textColor: "#94a3b8",
      fontSize: 12,
    },
    grid: {
      vertLines: { color: "#1e293b" },
      horzLines: { color: "#1e293b" },
    },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: "#1e293b" },
    timeScale: { borderColor: "#1e293b" },
  });

  // Volume histogram (rendered first so candles draw on top)
  volumeSeries = chart.addHistogramSeries({
    color: "rgba(59,130,246,.25)",
    priceFormat: { type: "volume" },
    priceScaleId: "volume",
  });
  chart.priceScale("volume").applyOptions({
    scaleMargins: { top: 0.8, bottom: 0 },
  });

  var volumeData = [];
  for (var vi = 0; vi < priceData.timestamps.length; vi++) {
    var volVal = priceData.volumes ? priceData.volumes[vi] : 0;
    var isUp = priceData.closes[vi] >= priceData.opens[vi];
    volumeData.push({
      time: tsToDate(priceData.timestamps[vi]),
      value: volVal,
      color: isUp ? "rgba(34,197,94,.35)" : "rgba(239,68,68,.35)",
    });
  }
  volumeSeries.setData(volumeData);

  // Candlestick series
  candleSeries = chart.addCandlestickSeries({
    upColor: "#22c55e",
    downColor: "#ef4444",
    borderUpColor: "#22c55e",
    borderDownColor: "#ef4444",
    wickUpColor: "#22c55e",
    wickDownColor: "#ef4444",
  });

  var candles = [];
  for (var i = 0; i < priceData.timestamps.length; i++) {
    candles.push({
      time: tsToDate(priceData.timestamps[i]),
      open: priceData.opens[i],
      high: priceData.highs[i],
      low: priceData.lows[i],
      close: priceData.closes[i],
    });
  }
  candleSeries.setData(candles);

  // MA20 line
  if (ta && ta.trend && ta.trend.ma20_series) {
    ma20Series = chart.addLineSeries({
      color: "#3b82f6",
      lineWidth: 2,
      title: "MA20",
    });
    var ma20Data = [];
    for (var j = 0; j < ta.trend.ma20_series.length; j++) {
      if (ta.trend.ma20_series[j] !== null) {
        ma20Data.push({ time: tsToDate(priceData.timestamps[j]), value: ta.trend.ma20_series[j] });
      }
    }
    ma20Series.setData(ma20Data);
  }

  // MA50 line
  if (ta && ta.trend && ta.trend.ma50_series) {
    ma50Series = chart.addLineSeries({
      color: "#f59e0b",
      lineWidth: 2,
      title: "MA50",
    });
    var ma50Data = [];
    for (var k = 0; k < ta.trend.ma50_series.length; k++) {
      if (ta.trend.ma50_series[k] !== null) {
        ma50Data.push({ time: tsToDate(priceData.timestamps[k]), value: ta.trend.ma50_series[k] });
      }
    }
    ma50Series.setData(ma50Data);
  }

  // Support line
  if (ta && ta.levels && ta.levels.nearest_support) {
    var supportLine = chart.addLineSeries({
      color: "#22c55e",
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      title: "Support",
    });
    supportLine.setData([
      { time: tsToDate(priceData.timestamps[0]), value: ta.levels.nearest_support },
      { time: tsToDate(priceData.timestamps[priceData.timestamps.length - 1]), value: ta.levels.nearest_support },
    ]);
  }

  // Resistance line
  if (ta && ta.levels && ta.levels.nearest_resistance) {
    var resistLine = chart.addLineSeries({
      color: "#ef4444",
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      title: "Resistance",
    });
    resistLine.setData([
      { time: tsToDate(priceData.timestamps[0]), value: ta.levels.nearest_resistance },
      { time: tsToDate(priceData.timestamps[priceData.timestamps.length - 1]), value: ta.levels.nearest_resistance },
    ]);
  }

  chart.timeScale().fitContent();

  resizeObserver = new ResizeObserver(() => chart.applyOptions({width: container.clientWidth}));
  resizeObserver.observe(container);
}

function render(data) {
  const s=data.signals, r=data.report;
  renderChart(data.price_data,s);
  $('quick-stats').hidden=false; $('analyst-card').hidden=false; $('evidence-card').hidden=false;
  text('stats-ticker',data.ticker + ' · latest bar ' + data.as_of);
  text('stats-price',fmt(s.current_price)); text('stats-ma20',fmt(s.trend.ma20)); text('stats-ma50',fmt(s.trend.ma50));
  text('stats-rsi',fmt(s.momentum.rsi));
  text('stats-volume',s.volume.latest == null ? null : fmt(s.volume.latest / 1e6,1)+'M');
  text('stats-vol-ratio',s.volume.ratio == null ? null : fmt(s.volume.ratio)+'×');
  $('verdict-badge-row').hidden=false;
  text('verdict-badge',r.verdict); $('verdict-badge').className='ta-verdict-badge '+tone(r.verdict);
  for (const [id,key] of [['trend','trend'],['momentum','momentum'],['vol','volatility'],['volume','volume']]) {
    text('badge-'+id,key + ': '+s[key].signal); $('badge-'+id).className='ta-badge '+tone(s[key].signal);
  }
  text('analyst-support',fmt(s.levels.nearest_support)); text('analyst-resistance',fmt(s.levels.nearest_resistance));
  text('analyst-confidence',s.momentum.one_month_return == null ? null : fmt(s.momentum.one_month_return)+'%');
  text('analyst-hint',s.volatility.realized_vol_20d == null ? null : fmt(s.volatility.realized_vol_20d)+'%');
  text('analyst-summary',r.summary); text('analyst-caution',r.caution); text('analyst-watch-next',r.watch_next);
  text('chart-readout',data.ticker+' · '+data.price_data.closes.length+' daily bars through '+data.as_of+' · Latest close '+fmt(s.current_price)+' in quote currency. Blue: MA20. Amber: MA50. Dashed: support / resistance.');
  trace('graph-trace',data.trace,'technical'); sources(data.sources); download(data,'technical');
}
function tone(value) {
  return ['bullish','supportive','low'].includes(value) ? 'badge-green' : ['bearish','weak','stretched','high'].includes(value) ? 'badge-red' : 'badge-amber';
}
async function analyze() {
  if (loading) return;
  const ticker=$('ticker-input').value.trim();
  if (!ticker) {status('Enter a ticker to analyze.',true); return;}
  loading=true; $('analyze-btn').disabled=true; $('ticker-input').disabled=true;
  text('analyze-btn','Analyzing…'); status(demo ? 'Running the synthetic sample…' : 'Gathering price history and preparing the report…');
  for (const id of ['quick-stats','analyst-card','evidence-card']) $(id).hidden=true;
  if (resizeObserver) resizeObserver.disconnect();
  if (chart) {chart.remove();chart=null;}
  $('chart-placeholder').hidden=false; text('chart-readout','');
  trace('graph-trace',[{name:'Analysis in progress',detail:'Completed steps will appear when the server finishes.'}],'technical');
  try {render(await request('technical',{ticker}));status();}
  catch (error) {status(error.message,true);trace('graph-trace',[{name:'Analysis unavailable',detail:'The workflow did not return a completed report.'}],'technical');}
  finally {loading=false; $('analyze-btn').disabled=false; $('ticker-input').disabled=false; text('analyze-btn','Analyze');}
}
$('analyze-btn').addEventListener('click',analyze);
$('ticker-input').addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();analyze();}});
})();
