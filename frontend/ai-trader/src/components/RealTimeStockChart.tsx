import React, { useState, useEffect, useRef, useCallback } from 'react';
import Chart from 'react-apexcharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { tradingApi, type StockInfo } from '../services/api';
import { 
  TrendingUp, 
  TrendingDown, 
  RefreshCw, 
  Play, 
  Pause,
  BarChart3
} from 'lucide-react';

interface ChartData {
  x: number;
  y: [number, number, number, number]; // OHLC format
}

interface PriceData {
  timestamp: number;
  price: number;
  volume: number;
}

const RealTimeStockChart: React.FC = () => {
  const [symbol, setSymbol] = useState('');
  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null);
  const [chartData, setChartData] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(false);
  const [isRealTime, setIsRealTime] = useState(false);
  const [interval, setInterval] = useState('1m');
  const [error, setError] = useState<string | null>(null);
  const [hasLoaded, setHasLoaded] = useState(false);
  
  const lastUpdateRef = useRef<number>(0);

  const generateChartData = (basePrice: number, interval: string, points: number) => {
    const now = Date.now();
    const data: ChartData[] = [];
    const prices: PriceData[] = [];
    
    // Calculate time intervals based on timeframe
    const timeIntervals = {
      '1m': 60 * 1000,
      '5m': 5 * 60 * 1000,
      '15m': 15 * 60 * 1000,
      '1h': 60 * 60 * 1000,
      '4h': 4 * 60 * 60 * 1000,
      '1d': 24 * 60 * 60 * 1000,
      '1w': 7 * 24 * 60 * 60 * 1000
    };
    
    const intervalMs = timeIntervals[interval as keyof typeof timeIntervals] || 60 * 1000;
    
    // Use a more stable price generation with trending
    let currentPrice = basePrice;
    const trend = (Math.random() - 0.5) * 0.001; // Small overall trend
    
    for (let i = points - 1; i >= 0; i--) {
      const timestamp = now - (i * intervalMs);
      
      // Apply trend and small random variation
      const trendChange = trend * (points - i);
      const randomVariation = (Math.random() - 0.5) * 0.005 * basePrice; // ±0.5% variation
      currentPrice = basePrice + trendChange + randomVariation;
      
      // Generate OHLC data with more realistic patterns
      const volatility = 0.002 * currentPrice; // 0.2% volatility
      const open = currentPrice + (Math.random() - 0.5) * volatility;
      const close = currentPrice + (Math.random() - 0.5) * volatility;
      const high = Math.max(open, close) + Math.random() * volatility;
      const low = Math.min(open, close) - Math.random() * volatility;
      
      data.push({
        x: timestamp,
        y: [open, high, low, close]
      });
      
      prices.push({
        timestamp,
        price: close,
        volume: Math.floor(Math.random() * 500000 + 500000) // 500K to 1M volume
      });
    }
    
    return { data, prices };
  };

  const loadStockData = useCallback(async () => {
    if (!symbol.trim()) {
      setError('Please enter a stock symbol');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await tradingApi.getStock(symbol.toUpperCase());
      setStockInfo(data);
      
      // Generate chart data based on interval
      const points = interval === '1w' ? 52 : interval === '1d' ? 30 : 50;
      const { data: chartData } = generateChartData(data.current_price, interval, points);
      
      setChartData(chartData);
      setHasLoaded(true);
      lastUpdateRef.current = Date.now();
      
    } catch (err) {
      setError(`Failed to load data for ${symbol.toUpperCase()}`);
      console.error('Error loading stock data:', err);
    } finally {
      setLoading(false);
    }
  }, [symbol, interval]);

  const toggleRealTime = () => {
    setIsRealTime(!isRealTime);
    if (!isRealTime) {
      // When enabling real-time, refresh data once
      loadStockData();
    }
  };

  // Remove all polling - only refresh on user interaction
  useEffect(() => {
    // No cleanup needed since we removed polling
  }, []);

  // Event-driven loading only
  useEffect(() => {
    if (symbol && !hasLoaded) {
      loadStockData();
    }
  }, [symbol, loadStockData, hasLoaded]);

  const chartOptions = {
    chart: {
      type: 'candlestick' as const,
      height: 400,
      background: 'transparent',
      toolbar: {
        show: true,
        tools: {
          download: true,
          selection: true,
          zoom: true,
          zoomin: true,
          zoomout: true,
          pan: true,
        }
      },
      animations: {
        enabled: isRealTime,
        speed: 800,
        animateGradually: {
          enabled: true,
          delay: 150
        }
      }
    },
    title: {
      text: `${symbol} - ${interval.toUpperCase()} Chart`,
      align: 'left' as const,
      style: {
        fontSize: '16px',
        fontWeight: 600
      }
    },
    xaxis: {
      type: 'datetime' as const,
      labels: {
        datetimeFormatter: {
          year: 'yyyy',
          month: 'MMM \'yy',
          day: 'dd MMM',
          hour: 'HH:mm',
          minute: 'HH:mm'
        }
      }
    },
    yaxis: {
      title: {
        text: 'Price ($)'
      },
      labels: {
        formatter: (value: number) => `$${value.toFixed(2)}`
      }
    },
    tooltip: {
      enabled: true,
      shared: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      custom: ({ seriesIndex, dataPointIndex, w }: { seriesIndex: number; dataPointIndex: number; w: any }) => {
        const o = w.globals.seriesCandleO[seriesIndex][dataPointIndex];
        const h = w.globals.seriesCandleH[seriesIndex][dataPointIndex];
        const l = w.globals.seriesCandleL[seriesIndex][dataPointIndex];
        const c = w.globals.seriesCandleC[seriesIndex][dataPointIndex];
        const timestamp = w.globals.seriesX[seriesIndex][dataPointIndex];
        
        return `
          <div class="p-2 bg-white border rounded shadow">
            <div class="font-semibold">${symbol}</div>
            <div class="text-sm text-gray-600">${new Date(timestamp).toLocaleString()}</div>
            <div class="mt-1">
              <div>Open: $${o?.toFixed(2)}</div>
              <div>High: $${h?.toFixed(2)}</div>
              <div>Low: $${l?.toFixed(2)}</div>
              <div>Close: $${c?.toFixed(2)}</div>
            </div>
          </div>
        `;
      }
    },
    plotOptions: {
      candlestick: {
        colors: {
          upward: '#10b981',
          downward: '#ef4444'
        },
        wick: {
          useFillColor: true
        }
      }
    },
    grid: {
      show: true,
      borderColor: '#e5e7eb',
      strokeDashArray: 0,
      position: 'back' as const
    }
  };

  const priceChangePercent = stockInfo?.change_percent || 0;
  const isPositiveChange = priceChangePercent >= 0;

  return (
    <div className="space-y-4">
      {/* Controls */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Real-Time Stock Chart
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                variant={isRealTime ? "default" : "outline"}
                size="sm"
                onClick={toggleRealTime}
                className="flex items-center gap-2"
                disabled={!hasLoaded}
              >
                {isRealTime ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                {isRealTime ? 'Live' : 'Start Live'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={loadStockData}
                disabled={loading || !symbol.trim()}
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 mb-4">
            <div className="flex items-center gap-2">
              <Input
                placeholder="Enter symbol (e.g., AAPL)"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                className="w-40"
                onKeyPress={(e) => e.key === 'Enter' && loadStockData()}
              />
              <Button 
                onClick={loadStockData} 
                disabled={loading || !symbol.trim()}
                className="flex items-center gap-2"
              >
                {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : null}
                Load
              </Button>
            </div>
            
            <Select value={interval} onValueChange={setInterval}>
              <SelectTrigger className="w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1m">1m</SelectItem>
                <SelectItem value="5m">5m</SelectItem>
                <SelectItem value="15m">15m</SelectItem>
                <SelectItem value="1h">1h</SelectItem>
                <SelectItem value="4h">4h</SelectItem>
                <SelectItem value="1d">1d</SelectItem>
                <SelectItem value="1w">1w</SelectItem>
              </SelectContent>
            </Select>
            
            {isRealTime && (
              <Badge variant="default" className="bg-green-100 text-green-800 border-green-200">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                Live
              </Badge>
            )}
          </div>

          {stockInfo && (
            <div className="flex items-center gap-4 mb-4">
              <div>
                <div className="text-2xl font-bold">${stockInfo.current_price.toFixed(2)}</div>
                <div className={`flex items-center gap-1 text-sm ${isPositiveChange ? 'text-green-600' : 'text-red-600'}`}>
                  {isPositiveChange ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                  {isPositiveChange ? '+' : ''}{priceChangePercent.toFixed(2)}%
                </div>
              </div>
              <div className="text-sm text-gray-600">
                <div>Volume: {stockInfo.volume?.toLocaleString()}</div>
                <div>Market Cap: ${stockInfo.market_cap?.toLocaleString()}</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Chart */}
      <Card>
        <CardContent className="p-6">
          {error ? (
            <div className="text-center py-8 text-red-600">
              <p>{error}</p>
              <Button onClick={loadStockData} className="mt-2">
                Retry
              </Button>
            </div>
          ) : chartData.length > 0 ? (
            <Chart
              options={chartOptions}
              series={[{
                name: symbol,
                data: chartData
              }]}
              type="candlestick"
              height={400}
            />
          ) : (
            <div className="text-center py-8 text-gray-500">
              {loading ? (
                <div className="flex items-center justify-center">
                  <RefreshCw className="h-6 w-6 animate-spin mr-2" />
                  Loading chart data...
                </div>
              ) : (
                <p>Enter a symbol and click Load to view the chart</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default RealTimeStockChart;
