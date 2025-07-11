import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Slider } from '@/components/ui/slider';
import SymbolManager from './SymbolManager';
import { automatedTradingApi, portfolioApi, type Portfolio } from '../services/api';
import { useEventDrivenData } from '../hooks/useEventDrivenData';
import { 
  Bot, 
  Play, 
  Square, 
  Activity, 
  TrendingUp, 
  AlertCircle,
  CheckCircle,
  BarChart3,
  RefreshCw,
  Settings,
  Brain,
  Shield,
  Target,
  Wifi,
  WifiOff
} from 'lucide-react';

interface EngineStatus {
  is_running: boolean;
  trading_mode: 'analysis_only' | 'full_control';
  daily_trade_count: number;
  max_daily_trades: number;
  monitored_symbols: string[];
  analysis_interval_seconds: number;
  min_confidence_threshold: number;
  last_trade_reset: string | null;
}

interface TradingModeInfo {
  current_mode: string;
  modes: {
    analysis_only: string;
    full_control: string;
  };
  confidence_threshold: number;
}

interface RecentActivity {
  recent_decisions: Array<{
    symbol: string;
    action: string;
    confidence: number;
    reasoning: string;
    created_at: string;
  }>;
  recent_trades_24h: Array<{
    symbol: string;
    action: string;
    quantity: number;
    price: number;
    timestamp: string;
  }>;
  total_decisions_today: number;
  total_trades_today: number;
  engine_status: EngineStatus;
}

const EnhancedTradingControl: React.FC = () => {
  const [engineStatus, setEngineStatus] = useState<EngineStatus | null>(null);
  const [modeInfo, setModeInfo] = useState<TradingModeInfo | null>(null);
  const [recentActivity, setRecentActivity] = useState<RecentActivity | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [manualSymbol, setManualSymbol] = useState('');
  const [manualAnalysisLoading, setManualAnalysisLoading] = useState(false);
  const [confidenceThreshold, setConfidenceThreshold] = useState([75]);
  const [newUpdatesCount, setNewUpdatesCount] = useState(0);

  // Event-driven data fetching for real-time updates
  const {
    data: eventData,
    error: dataError,
    refreshAfterAction,
    refreshData
  } = useEventDrivenData();

  // Extract data from event-driven response
  const aiDecisions = eventData.aiDecisions;
  const tradeExecutions = eventData.tradeExecutions;
  const wsEngineStatus = eventData.engineStatus;
  const portfolioUpdates = eventData.portfolioUpdate;
  
  // Connection status based on data fetching
  const wsConnected = !dataError;
  const connectionState = dataError ? 'error' : 'connected';

  // Initial data fetch on component mount
  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // Update local state when event data arrives
  useEffect(() => {
    if (wsEngineStatus) {
      // Map websocket engine status to local engine status format
      setEngineStatus(prev => ({
        ...prev,
        is_running: wsEngineStatus.is_running,
        trading_mode: prev?.trading_mode || 'analysis_only',
        daily_trade_count: prev?.daily_trade_count || 0,
        max_daily_trades: prev?.max_daily_trades || 10,
        monitored_symbols: prev?.monitored_symbols || [],
        analysis_interval_seconds: prev?.analysis_interval_seconds || 300,
        min_confidence_threshold: prev?.min_confidence_threshold || 0.75,
        last_trade_reset: wsEngineStatus.last_run || prev?.last_trade_reset || null
      }));
    }
  }, [wsEngineStatus]);

  useEffect(() => {
    if (portfolioUpdates) {
      // Convert portfolio update format to match expected Portfolio type
      const convertedPortfolio: Portfolio = {
        ...portfolioUpdates,
        holdings: portfolioUpdates.holdings.map(holding => ({
          symbol: holding.symbol,
          quantity: holding.quantity,
          avg_price: holding.average_price,
          current_price: holding.current_price,
          value: holding.market_value,
          profit_loss: holding.profit_loss
        }))
      };
      setPortfolio(convertedPortfolio);
    }
  }, [portfolioUpdates]);

  // Update recent activity with real-time data
  useEffect(() => {
    if (aiDecisions.length > 0 || tradeExecutions.length > 0) {
      setRecentActivity(prev => {
        if (!prev) return null;
        
        // Convert websocket decision format to expected format
        const convertedDecisions = aiDecisions.map(decision => ({
          symbol: decision.symbol,
          action: decision.action,
          confidence: decision.confidence,
          reasoning: decision.reasoning,
          created_at: decision.timestamp
        }));

        // Convert websocket trade format to expected format
        const convertedTrades = tradeExecutions.map(trade => ({
          symbol: trade.symbol,
          action: trade.action,
          quantity: trade.quantity,
          price: trade.price,
          timestamp: trade.timestamp
        }));

        // Check if there are new updates
        const hasNewDecisions = convertedDecisions.length > prev.recent_decisions.length;
        const hasNewTrades = convertedTrades.length > prev.recent_trades_24h.length;
        
        if (hasNewDecisions || hasNewTrades) {
          setNewUpdatesCount(prev => prev + 1);
          // Show success message for new activity
          setSuccess(
            hasNewDecisions && hasNewTrades 
              ? 'New AI decision and trade executed!'
              : hasNewDecisions 
                ? 'New AI trading decision received!'
                : 'New trade executed!'
          );
          // Clear success message after 5 seconds
          setTimeout(() => setSuccess(null), 5000);
        }

        return {
          ...prev,
          recent_decisions: convertedDecisions.slice(0, 10),
          recent_trades_24h: convertedTrades.slice(0, 10),
          total_decisions_today: prev.total_decisions_today + (hasNewDecisions ? 1 : 0),
          total_trades_today: prev.total_trades_today + (hasNewTrades ? 1 : 0)
        };
      });
    }
  }, [aiDecisions, tradeExecutions]);
  const loadEngineStatus = useCallback(async () => {
    try {
      const data = await automatedTradingApi.getStatus();
      setEngineStatus(data);
      if (data.min_confidence_threshold) {
        setConfidenceThreshold([data.min_confidence_threshold * 100]);
      }
    } catch (error) {
      console.error('Error loading engine status:', error);
    }
  }, []);

  const loadModeInfo = useCallback(async () => {
    try {
      const data = await automatedTradingApi.getMode();
      setModeInfo(data);
    } catch (error) {
      console.error('Error loading mode info:', error);
    }
  }, []);

  const loadRecentActivity = useCallback(async () => {
    try {
      const data = await automatedTradingApi.getRecentActivity();
      setRecentActivity(data);
    } catch (error) {
      console.error('Error loading recent activity:', error);
    }
  }, []);

  const loadPortfolio = useCallback(async () => {
    try {
      const data = await portfolioApi.getPortfolio();
      setPortfolio(data);
    } catch (error) {
      console.error('Error loading portfolio:', error);
    }
  }, []);

  const loadAllData = useCallback(async () => {
    try {
      await Promise.all([
        loadEngineStatus(),
        loadModeInfo(),
        loadRecentActivity(),
        loadPortfolio()
      ]);
    } catch (error) {
      console.error('Error loading data:', error);
    }
  }, [loadEngineStatus, loadModeInfo, loadRecentActivity, loadPortfolio]);

  useEffect(() => {
    loadAllData();
    // No more automatic refreshing - only event-driven updates
  }, [loadAllData]);

  const startEngine = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await automatedTradingApi.start();
      await loadEngineStatus();
      await refreshAfterAction('Engine started');
      setSuccess('Trading engine started successfully');
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : 'Failed to start engine');
    } finally {
      setLoading(false);
    }
  };

  const stopEngine = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await automatedTradingApi.stop();
      await loadEngineStatus();
      await refreshAfterAction('Engine stopped');
      setSuccess('Trading engine stopped successfully');
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : 'Failed to stop engine');
    } finally {
      setLoading(false);
    }
  };

  const setTradingMode = async (mode: 'analysis_only' | 'full_control') => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await automatedTradingApi.setMode(mode);
      await loadModeInfo();
      await refreshAfterAction(`Trading mode set to ${mode}`);
      setSuccess(response.message);
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : 'Failed to set trading mode');
    } finally {
      setLoading(false);
    }
  };

  const updateConfidenceThreshold = async (threshold: number) => {
    try {
      await automatedTradingApi.updateConfidenceThreshold(threshold / 100);
      await loadEngineStatus();
      await refreshAfterAction(`Confidence threshold updated to ${threshold}%`);
      setSuccess(`Confidence threshold updated to ${threshold}%`);
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : 'Failed to update confidence threshold');
    }
  };

  const executeManualAnalysis = async () => {
    if (!manualSymbol.trim()) return;
    
    setManualAnalysisLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      const result = await automatedTradingApi.executeManualAnalysis(manualSymbol.trim());
      setManualSymbol('');
      await loadRecentActivity();
      setSuccess(`Analysis completed for ${result.symbol}: ${result.decision.action} (${(result.decision.confidence * 100).toFixed(1)}% confidence)`);
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : 'Failed to execute manual analysis');
    } finally {
      setManualAnalysisLoading(false);
    }
  };

  const clearMessages = () => {
    setError(null);
    setSuccess(null);
  };

  const formatTime = (isoString: string) => {
    return new Date(isoString).toLocaleString();
  };

  const getModeColor = (mode: string) => {
    return mode === 'full_control' ? 'bg-orange-100 text-orange-800' : 'bg-blue-100 text-blue-800';
  };

  const getModeIcon = (mode: string) => {
    return mode === 'full_control' ? <Bot className="h-4 w-4" /> : <Brain className="h-4 w-4" />;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="h-6 w-6 text-blue-600" />
          <h2 className="text-2xl font-bold">AI Trading Engine</h2>
          {/* WebSocket Status Indicator */}
          <div className="flex items-center gap-1" title={wsConnected ? "Connected to real-time updates" : `Disconnected (${connectionState})`}>
            {wsConnected ? (
              <Wifi className="h-4 w-4 text-green-500" />
            ) : (
              <WifiOff className="h-4 w-4 text-red-500" />
            )}
            <span className="text-xs text-gray-500">
              {wsConnected ? 'Live' : 'Offline'}
            </span>
          </div>
        </div>
        <Button onClick={loadAllData} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Status Messages */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            {error}
            <Button variant="ghost" size="sm" onClick={clearMessages}>
              ×
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert className="border-green-200 bg-green-50">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertDescription className="flex items-center justify-between text-green-800">
            {success}
            <Button variant="ghost" size="sm" onClick={clearMessages}>
              ×
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Main Tabs */}
      <Tabs defaultValue="control" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
          <TabsTrigger value="symbols">Symbols</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>


        <TabsContent value="portfolio" className="space-y-6">
          {/* Portfolio Overview */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Current Portfolio Status
              </CardTitle>
              <CardDescription>
                Holdings being monitored by the AI trading engine
              </CardDescription>
            </CardHeader>
            <CardContent>
              {portfolio ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="text-sm text-gray-600">Total Value</div>
                      <div className="text-2xl font-bold text-gray-900">
                        ${portfolio.total_value?.toLocaleString() || '0'}
                      </div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="text-sm text-gray-600">Available Cash</div>
                      <div className="text-2xl font-bold text-gray-900">
                        ${portfolio.cash_balance?.toLocaleString() || '0'}
                      </div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="text-sm text-gray-600">Total P&L</div>
                      <div className={`text-2xl font-bold ${
                        (portfolio.profit_loss || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {(portfolio.profit_loss || 0) >= 0 ? '+' : ''}
                        ${(portfolio.profit_loss || 0).toLocaleString()}
                      </div>
                    </div>
                  </div>

                  {portfolio.holdings && portfolio.holdings.length > 0 ? (
                    <div className="space-y-3">
                      <h3 className="font-semibold">Current Holdings</h3>
                      {portfolio.holdings.map((holding, index: number) => (
                        <div key={index} className="border rounded-lg p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <Badge variant="outline" className="font-mono">
                                {holding.symbol}
                              </Badge>
                              <div>
                                <div className="font-medium">{holding.quantity} shares</div>
                                <div className="text-sm text-gray-600">
                                  Avg. ${holding.avg_price?.toFixed(2)}
                                </div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="font-semibold">
                                ${(holding.quantity * (holding.current_price || holding.avg_price)).toLocaleString()}
                              </div>
                              <div className={`text-sm ${
                                (holding.current_price || 0) >= (holding.avg_price || 0) 
                                  ? 'text-green-600' : 'text-red-600'
                              }`}>
                                {(holding.current_price || 0) >= (holding.avg_price || 0) ? '+' : ''}
                                {(((holding.current_price || holding.avg_price) - holding.avg_price) / holding.avg_price * 100).toFixed(2)}%
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <BarChart3 className="h-12 w-12 mx-auto text-gray-300 mb-4" />
                      <p>No current holdings</p>
                      <p className="text-sm mt-2">The AI will make recommendations based on market analysis</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8">
                  <RefreshCw className="h-6 w-6 animate-spin mx-auto text-gray-400" />
                  <p className="text-gray-500 mt-2">Loading portfolio data...</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="symbols">
          <SymbolManager />
        </TabsContent>

        <TabsContent value="activity" className="space-y-6">
          {/* Recent Activity */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  Recent AI Decisions
                  {wsConnected && newUpdatesCount > 0 && (
                    <Badge variant="secondary" className="text-xs animate-pulse">
                      Live
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription>Latest AI trading recommendations and analysis</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {recentActivity?.recent_decisions.slice(0, 5).map((decision, index) => (
                    <div key={index} className="border rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{decision.symbol}</Badge>
                          <Badge 
                            className={
                              decision.action === 'buy' ? 'bg-green-100 text-green-800' :
                              decision.action === 'sell' ? 'bg-red-100 text-red-800' :
                              'bg-yellow-100 text-yellow-800'
                            }
                          >
                            {decision.action.toUpperCase()}
                          </Badge>
                        </div>
                        <div className="text-sm text-gray-500">
                          {(decision.confidence * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div className="text-sm text-gray-600">
                        {decision.reasoning}
                      </div>
                      <div className="text-xs text-gray-400 mt-2">
                        {formatTime(decision.created_at)}
                      </div>
                    </div>
                  )) || (
                    <div className="text-center py-4 text-gray-500">
                      No recent decisions
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  Recent Trades (24h)
                  {wsConnected && newUpdatesCount > 0 && (
                    <Badge variant="secondary" className="text-xs animate-pulse">
                      Live
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription>Executed trades in the last 24 hours</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {recentActivity?.recent_trades_24h.slice(0, 5).map((trade, index) => (
                    <div key={index} className="border rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{trade.symbol}</Badge>
                          <Badge 
                            className={
                              trade.action === 'buy' ? 'bg-green-100 text-green-800' :
                              'bg-red-100 text-red-800'
                            }
                          >
                            {trade.action.toUpperCase()}
                          </Badge>
                        </div>
                        <div className="text-sm font-medium">
                          ${(trade.price * trade.quantity).toFixed(2)}
                        </div>
                      </div>
                      <div className="text-sm text-gray-600">
                        {trade.quantity} shares @ ${trade.price.toFixed(2)}
                      </div>
                      <div className="text-xs text-gray-400 mt-2">
                        {formatTime(trade.timestamp)}
                      </div>
                    </div>
                  )) || (
                    <div className="text-center py-4 text-gray-500">
                      No recent trades
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Summary Stats */}
          {recentActivity && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Today's Summary</CardTitle>
                <CardDescription>Current trading session statistics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {recentActivity.total_decisions_today}
                    </div>
                    <div className="text-sm text-gray-500">AI Decisions</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {recentActivity.total_trades_today}
                    </div>
                    <div className="text-sm text-gray-500">Trades Executed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-600">
                      {engineStatus?.monitored_symbols.length || 0}
                    </div>
                    <div className="text-sm text-gray-500">Symbols Monitored</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-orange-600">
                      {(engineStatus?.min_confidence_threshold || 0) * 100}%
                    </div>
                    <div className="text-sm text-gray-500">Min Confidence</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default EnhancedTradingControl;
