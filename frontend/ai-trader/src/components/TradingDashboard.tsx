import React, { useState, useEffect, useCallback } from 'react';
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
  Bot,
  Settings,
  MessageCircle,
  Loader2
} from 'lucide-react';
import { 
  portfolioApi, 
  tradingApi, 
  newsApi, 
  companySearchApi,
  type Portfolio, 
  type StockInfo, 
  type NewsItem, 
  type TradeDecision 
} from '../services/api';
import PortfolioOverview from './PortfolioOverview';
import StockAnalysis from './StockAnalysis';
import NewsSection from './NewsSection';
import TradeHistory from './TradeHistory';
import AIAnalyticsDashboard from './AIAnalyticsDashboard';
import NewsAnalysisComponent from './NewsAnalysisComponent';
import RealTimeStockChart from './RealTimeStockChart';
import AIInsightsSummary from './AIInsightsSummary';
import EnhancedTradingControl from './EnhancedTradingControl';

interface TradingDashboardProps {
  onShowOnboarding?: () => void;
}

const TradingDashboard: React.FC<TradingDashboardProps> = ({ onShowOnboarding }) => {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchSymbol, setSearchSymbol] = useState('');
  const [currentAnalysis, setCurrentAnalysis] = useState<{
    stock: StockInfo;
    decision: TradeDecision;
  } | null>(null);
  const [newsLoaded, setNewsLoaded] = useState(false);
  const [searchMode, setSearchMode] = useState<'symbol' | 'company'>('symbol');

  useEffect(() => {
    loadInitialData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const loadInitialData = useCallback(async () => {
    setLoading(true);
    try {
      // Always load portfolio, but only load news if not already loaded
      const portfolioPromise = portfolioApi.getPortfolio();
      const newsPromise = newsLoaded ? Promise.resolve(news) : newsApi.getFinancialNews(10);
      
      const [portfolioData, newsData] = await Promise.all([
        portfolioPromise,
        newsPromise
      ]);
      
      setPortfolio(portfolioData);
      if (!newsLoaded) {
        setNews(newsData);
        setNewsLoaded(true);
      }
    } catch (err) {
      setError('Failed to load initial data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [newsLoaded, news]);

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
    setCurrentAnalysis(null); // Clear previous analysis
    
    try {
      let symbolToAnalyze = searchSymbol.trim();
      
      // If in company mode, resolve company name to symbol first
      if (searchMode === 'company') {
        const resolution = await companySearchApi.resolveSymbol(symbolToAnalyze, 'company');
        if (resolution.resolved && resolution.symbol) {
          symbolToAnalyze = resolution.symbol;
        } else {
          throw new Error(`Could not find symbol for company: ${symbolToAnalyze}`);
        }
      } else {
        // In symbol mode, just verify the symbol is valid
        const resolution = await companySearchApi.resolveSymbol(symbolToAnalyze, 'symbol');
        if (!resolution.resolved) {
          throw new Error(`Invalid stock symbol: ${symbolToAnalyze}`);
        }
        symbolToAnalyze = symbolToAnalyze.toUpperCase();
      }
      
      const [stockInfo, decision] = await Promise.all([
        tradingApi.getStock(symbolToAnalyze),
        tradingApi.analyzeStock(symbolToAnalyze)
      ]);
      
      setCurrentAnalysis({ stock: stockInfo, decision });
    } catch (err) {
      const errorMessage = searchMode === 'company' 
        ? `Failed to analyze company "${searchSymbol}". Please check the company name and try again.`
        : `Failed to analyze "${searchSymbol}". Please check the stock symbol and try again.`;
      setError(errorMessage);
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
        price: decision.suggested_price,
        decision_id: decision.decision_id
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

      {/* AI Insights Summary */}
      <AIInsightsSummary />

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
            Stock Analysis
          </CardTitle>
          <CardDescription>
            Enter a stock symbol or company name for AI trading recommendations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex space-x-2 mb-4">
            <div className="flex-1 space-y-2">
              <div className="flex space-x-2">
                <Button
                  variant={searchMode === 'symbol' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSearchMode('symbol')}
                  className="flex-1"
                >
                  Stock Symbol
                </Button>
                <Button
                  variant={searchMode === 'company' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSearchMode('company')}
                  className="flex-1"
                >
                  Company Name
                </Button>
              </div>
              <Input
                placeholder={searchMode === 'symbol' 
                  ? "Enter stock symbol (e.g., AAPL, TSLA, NVDA)" 
                  : "Enter company name (e.g., Apple, Tesla, Microsoft)"}
                value={searchSymbol}
                onChange={(e) => {
                  const newValue = e.target.value;
                  setSearchSymbol(newValue);
                  // Clear previous analysis when user starts typing a new symbol
                  if (newValue !== searchSymbol && currentAnalysis) {
                    setCurrentAnalysis(null);
                    setError(null);
                  }
                }}
                onKeyPress={(e) => e.key === 'Enter' && analyzeStock()}
              />
            </div>
            <Button onClick={analyzeStock} disabled={loading || !searchSymbol.trim()}>
              <Search className="h-4 w-4 mr-2" />
              {loading ? 'Analyzing...' : 'Analyze'}
              {loading && (
                <Loader2 className="h-4 w-4 ml-2 animate-spin" />
              )}
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
        <TabsList className="grid w-full grid-cols-8">
          <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
          <TabsTrigger value="news">Market News</TabsTrigger>
          <TabsTrigger value="history">Trade History</TabsTrigger>
          <TabsTrigger value="ai-analytics">AI Analytics</TabsTrigger>
          <TabsTrigger value="news-analysis">News Analysis</TabsTrigger>
          <TabsTrigger value="stock-charts">Stock Charts</TabsTrigger>
          <TabsTrigger value="automated-trading">Auto Trading</TabsTrigger>
          <TabsTrigger value="preferences">Preferences</TabsTrigger>
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

        <TabsContent value="ai-analytics" className="space-y-4">
          <AIAnalyticsDashboard />
        </TabsContent>

        <TabsContent value="news-analysis" className="space-y-4">
          <NewsAnalysisComponent />
        </TabsContent>

        <TabsContent value="stock-charts" className="space-y-4">
          <RealTimeStockChart />
        </TabsContent>

        <TabsContent value="automated-trading" className="space-y-4">
          <EnhancedTradingControl />
        </TabsContent>

        <TabsContent value="preferences" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="w-5 h-5" />
                Investment Preferences
              </CardTitle>
              <CardDescription>
                Manage your investment preferences and onboarding settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-center py-8">
                <MessageCircle className="w-16 h-16 text-blue-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">Update Your Investment Profile</h3>
                <p className="text-gray-600 mb-6 max-w-md mx-auto">
                  Chat with our AI advisor to update your investment preferences, risk tolerance, 
                  and trading goals to get better personalized recommendations.
                </p>
                <Button 
                  onClick={onShowOnboarding}
                  className="flex items-center gap-2"
                  size="lg"
                >
                  <MessageCircle className="w-4 h-4" />
                  Start Preferences Chat
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default TradingDashboard;
