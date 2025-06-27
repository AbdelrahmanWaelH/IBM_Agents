import React, { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Alert, AlertDescription } from './ui/alert';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Activity, 
  BarChart3,
  RefreshCw,
  Search,
  Bot
} from 'lucide-react';
import { 
  portfolioApi, 
  tradingApi, 
  newsApi, 
  type Portfolio, 
  type StockInfo, 
  type NewsItem, 
  type TradeDecision 
} from '../services/api';
import PortfolioOverview from './PortfolioOverview';
import StockAnalysis from './StockAnalysis';
import NewsSection from './NewsSection';
import TradeHistory from './TradeHistory';

const TradingDashboard: React.FC = () => {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchSymbol, setSearchSymbol] = useState('');
  const [currentAnalysis, setCurrentAnalysis] = useState<{
    stock: StockInfo;
    decision: TradeDecision;
  } | null>(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [portfolioData, newsData] = await Promise.all([
        portfolioApi.getPortfolio(),
        newsApi.getFinancialNews(10)
      ]);
      
      setPortfolio(portfolioData);
      setNews(newsData);
    } catch (err) {
      setError('Failed to load initial data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const refreshPortfolio = async () => {
    try {
      const portfolioData = await portfolioApi.getPortfolio();
      setPortfolio(portfolioData);
    } catch (error) {
      setError('Failed to refresh portfolio');
      console.error('Portfolio refresh error:', error);
    }
  };

  const analyzeStock = async () => {
    if (!searchSymbol.trim()) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const [stockInfo, decision] = await Promise.all([
        tradingApi.getStock(searchSymbol.toUpperCase()),
        tradingApi.analyzeStock(searchSymbol.toUpperCase())
      ]);
      
      setCurrentAnalysis({ stock: stockInfo, decision });
    } catch (err) {
      setError(`Failed to analyze ${searchSymbol.toUpperCase()}`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const executeTrade = async (decision: TradeDecision) => {
    if (decision.action === 'hold') return;
    
    try {
      await tradingApi.executeTrade({
        symbol: decision.symbol,
        action: decision.action,
        quantity: decision.quantity,
        price: decision.suggested_price
      });
      
      // Refresh portfolio after trade
      await refreshPortfolio();
      
      // Show success message
      setError(null);
    } catch (err) {
      setError(`Failed to execute ${decision.action} order for ${decision.symbol}`);
      console.error(err);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatPercent = (percent: number) => {
    return `${percent >= 0 ? '+' : ''}${percent.toFixed(2)}%`;
  };

  if (loading && !portfolio) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading trading dashboard...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Portfolio Summary */}
      {portfolio && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Value</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(portfolio.total_value)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Cash Balance</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(portfolio.cash_balance)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">P&L</CardTitle>
              {portfolio.profit_loss >= 0 ? (
                <TrendingUp className="h-4 w-4 text-green-600" />
              ) : (
                <TrendingDown className="h-4 w-4 text-red-600" />
              )}
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${
                portfolio.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {formatCurrency(portfolio.profit_loss)}
              </div>
              <p className={`text-xs ${
                portfolio.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {formatPercent(portfolio.profit_loss_percent)}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Holdings</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{portfolio.holdings.length}</div>
              <p className="text-xs text-muted-foreground">Active positions</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Stock Analysis Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Bot className="h-5 w-5 mr-2" />
            AI Stock Analysis
          </CardTitle>
          <CardDescription>
            Enter a stock symbol to get AI-powered trading recommendations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex space-x-2 mb-4">
            <Input
              placeholder="Enter stock symbol (e.g., AAPL, TSLA, NVDA)"
              value={searchSymbol}
              onChange={(e) => setSearchSymbol(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && analyzeStock()}
            />
            <Button onClick={analyzeStock} disabled={loading || !searchSymbol.trim()}>
              <Search className="h-4 w-4 mr-2" />
              Analyze
            </Button>
          </div>

          {currentAnalysis && (
            <StockAnalysis 
              stock={currentAnalysis.stock}
              decision={currentAnalysis.decision}
              onExecuteTrade={executeTrade}
            />
          )}
        </CardContent>
      </Card>

      {/* Main Dashboard Tabs */}
      <Tabs defaultValue="portfolio" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
          <TabsTrigger value="news">Market News</TabsTrigger>
          <TabsTrigger value="history">Trade History</TabsTrigger>
        </TabsList>

        <TabsContent value="portfolio" className="space-y-4">
          <PortfolioOverview portfolio={portfolio} onRefresh={refreshPortfolio} />
        </TabsContent>

        <TabsContent value="news" className="space-y-4">
          <NewsSection news={news} onRefresh={() => loadInitialData()} />
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <TradeHistory />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default TradingDashboard;
