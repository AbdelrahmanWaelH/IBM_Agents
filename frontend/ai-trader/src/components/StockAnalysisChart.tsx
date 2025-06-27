import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { analyticsApi, type StockAnalysis } from '@/services/api';
import { TrendingUp, TrendingDown, BarChart3, Activity } from 'lucide-react';

const StockAnalysisChart: React.FC = () => {
  const [stockData, setStockData] = useState<StockAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchSymbol, setSearchSymbol] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');

  useEffect(() => {
    loadStockAnalysis();
  }, []);

  const loadStockAnalysis = async (symbol?: string) => {
    try {
      setLoading(true);
      const data = await analyticsApi.getStockAnalysis(symbol, 100);
      setStockData(data);
      if (symbol) {
        setSelectedSymbol(symbol);
      }
    } catch (error) {
      console.error('Error loading stock analysis:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    loadStockAnalysis(searchSymbol || undefined);
  };

  const formatNumber = (num: number) => {
    if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`;
    if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
    if (num >= 1e3) return `$${(num / 1e3).toFixed(2)}K`;
    return `$${num.toFixed(2)}`;
  };

  const formatVolume = (volume: number) => {
    if (volume >= 1e9) return `${(volume / 1e9).toFixed(2)}B`;
    if (volume >= 1e6) return `${(volume / 1e6).toFixed(2)}M`;
    if (volume >= 1e3) return `${(volume / 1e3).toFixed(2)}K`;
    return volume.toString();
  };

  const getChangeColor = (change: number) => {
    if (change > 0) return 'text-green-600';
    if (change < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  const getChangeIcon = (change: number) => {
    if (change > 0) return <TrendingUp className="h-4 w-4 text-green-500" />;
    if (change < 0) return <TrendingDown className="h-4 w-4 text-red-500" />;
    return <Activity className="h-4 w-4 text-gray-500" />;
  };

  // Group data by symbol for better visualization
  const groupedData = stockData.reduce((acc, item) => {
    if (!acc[item.symbol]) {
      acc[item.symbol] = [];
    }
    acc[item.symbol].push(item);
    return acc;
  }, {} as Record<string, StockAnalysis[]>);

  // Get unique symbols for overview
  const symbols = Object.keys(groupedData);
  const latestDataBySymbol = symbols.map(symbol => {
    const symbolData = groupedData[symbol];
    return symbolData.sort((a, b) => 
      new Date(b.analyzed_at).getTime() - new Date(a.analyzed_at).getTime()
    )[0];
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-6 w-6 text-blue-600" />
          <h2 className="text-2xl font-bold">Stock Analysis</h2>
        </div>
        <div className="flex gap-2">
          <Input
            placeholder="Search symbol..."
            value={searchSymbol}
            onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            className="w-48"
          />
          <Button onClick={handleSearch} variant="outline">
            Search
          </Button>
          <Button onClick={() => loadStockAnalysis()} variant="outline">
            Show All
          </Button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Stocks Analyzed</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{symbols.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Records</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stockData.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Gainers</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {latestDataBySymbol.filter(item => (item.change_percent || 0) > 0).length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Losers</CardTitle>
            <TrendingDown className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {latestDataBySymbol.filter(item => (item.change_percent || 0) < 0).length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Stock Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {latestDataBySymbol.map((stock) => (
          <Card key={stock.symbol} className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-xl">{stock.symbol}</CardTitle>
                <Badge variant="outline">
                  {getChangeIcon(stock.change_percent || 0)}
                  <span className={`ml-1 ${getChangeColor(stock.change_percent || 0)}`}>
                    {(stock.change_percent || 0).toFixed(2)}%
                  </span>
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500">Current Price</span>
                  <span className="font-bold text-lg">
                    ${stock.current_price.toFixed(2)}
                  </span>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500">Market Cap</span>
                  <span className="font-medium">
                    {formatNumber(stock.market_cap || 0)}
                  </span>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500">Volume</span>
                  <span className="font-medium">
                    {formatVolume(stock.volume || 0)}
                  </span>
                </div>
              </div>
              
              <div className="pt-2 border-t">
                <div className="text-xs text-gray-400">
                  Last analyzed: {new Date(stock.analyzed_at).toLocaleString()}
                </div>
              </div>

              <Button
                variant="outline"
                className="w-full"
                onClick={() => {
                  setSelectedSymbol(stock.symbol);
                  loadStockAnalysis(stock.symbol);
                }}
              >
                View History
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Historical Data for Selected Symbol */}
      {selectedSymbol && groupedData[selectedSymbol] && (
        <Card>
          <CardHeader>
            <CardTitle>
              {selectedSymbol} - Historical Analysis
            </CardTitle>
            <CardDescription>
              Price and volume data over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {groupedData[selectedSymbol]
                .sort((a, b) => new Date(b.analyzed_at).getTime() - new Date(a.analyzed_at).getTime())
                .slice(0, 20)
                .map((record, index) => (
                  <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className="text-center">
                        <div className="font-bold text-lg">
                          ${record.current_price.toFixed(2)}
                        </div>
                        <div className={`text-sm ${getChangeColor(record.change_percent || 0)}`}>
                          {(record.change_percent || 0).toFixed(2)}%
                        </div>
                      </div>
                      <div className="text-sm text-gray-500">
                        <div>MC: {formatNumber(record.market_cap || 0)}</div>
                        <div>Vol: {formatVolume(record.volume || 0)}</div>
                      </div>
                    </div>
                    <div className="text-right text-sm text-gray-400">
                      {new Date(record.analyzed_at).toLocaleString()}
                    </div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      {stockData.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">
              No stock analysis data found. Start analyzing stocks to see historical data here.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default StockAnalysisChart;
