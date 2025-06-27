import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import SymbolManager from './SymbolManager';
import { 
  Bot, 
  Play, 
  Square, 
  Activity, 
  TrendingUp, 
  AlertCircle,
  CheckCircle,
  BarChart3,
  RefreshCw
} from 'lucide-react';

interface EngineStatus {
  is_running: boolean;
  daily_trade_count: number;
  max_daily_trades: number;
  monitored_symbols: string[];
  analysis_interval_seconds: number;
  last_trade_reset: string | null;
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

const AutomatedTradingControlTabs: React.FC = () => {
  const [engineStatus, setEngineStatus] = useState<EngineStatus | null>(null);
  const [recentActivity, setRecentActivity] = useState<RecentActivity | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manualSymbol, setManualSymbol] = useState('');
  const [manualAnalysisLoading, setManualAnalysisLoading] = useState(false);

  useEffect(() => {
    loadEngineStatus();
    loadRecentActivity();
    
    // Refresh status every 30 seconds
    const interval = setInterval(() => {
      loadEngineStatus();
      loadRecentActivity();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const loadEngineStatus = async () => {
    try {
      const response = await fetch('/api/automated-trading/status');
      if (response.ok) {
        const data = await response.json();
        setEngineStatus(data);
      }
    } catch (error) {
      console.error('Error loading engine status:', error);
    }
  };

  const loadRecentActivity = async () => {
    try {
      const response = await fetch('/api/automated-trading/recent-activity');
      if (response.ok) {
        const data = await response.json();
        setRecentActivity(data);
      }
    } catch (error) {
      console.error('Error loading recent activity:', error);
    }
  };

  const startEngine = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/automated-trading/start', {
        method: 'POST'
      });
      
      if (response.ok) {
        await loadEngineStatus();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to start engine');
      }
    } catch (error) {
      setError('Error starting engine');
      console.error('Error starting engine:', error);
    } finally {
      setLoading(false);
    }
  };

  const stopEngine = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/automated-trading/stop', {
        method: 'POST'
      });
      
      if (response.ok) {
        await loadEngineStatus();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to stop engine');
      }
    } catch (error) {
      setError('Error stopping engine');
      console.error('Error stopping engine:', error);
    } finally {
      setLoading(false);
    }
  };

  const executeManualAnalysis = async () => {
    if (!manualSymbol.trim()) return;
    
    setManualAnalysisLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/automated-trading/execute-manual-analysis?symbol=${manualSymbol.trim()}`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Manual analysis result:', data);
        setManualSymbol('');
        // Refresh recent activity to show the new decision
        await loadRecentActivity();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to execute analysis');
      }
    } catch (error) {
      setError('Error executing manual analysis');
      console.error('Error executing manual analysis:', error);
    } finally {
      setManualAnalysisLoading(false);
    }
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Main Tabs */}
      <Tabs defaultValue="control" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="control">Trading Control</TabsTrigger>
          <TabsTrigger value="symbols">Symbol Management</TabsTrigger>
          <TabsTrigger value="activity">Recent Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="control" className="space-y-6">
          {/* Engine Control */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5" />
                Automated Trading Engine
              </CardTitle>
              <CardDescription>
                Start or stop the automated trading engine
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    {engineStatus?.is_running ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <AlertCircle className="h-5 w-5 text-gray-400" />
                    )}
                    <span className="font-medium">
                      Status: {engineStatus?.is_running ? 'Running' : 'Stopped'}
                    </span>
                  </div>
                  {engineStatus?.is_running && (
                    <Badge variant="default" className="bg-green-100 text-green-800">
                      <Activity className="h-3 w-3 mr-1" />
                      Active
                    </Badge>
                  )}
                </div>
                
                <div className="flex gap-2">
                  {engineStatus?.is_running ? (
                    <Button 
                      onClick={stopEngine} 
                      disabled={loading} 
                      variant="destructive"
                    >
                      <Square className="h-4 w-4 mr-2" />
                      Stop Engine
                    </Button>
                  ) : (
                    <Button 
                      onClick={startEngine} 
                      disabled={loading}
                      className="bg-green-600 hover:bg-green-700"
                    >
                      <Play className="h-4 w-4 mr-2" />
                      Start Engine
                    </Button>
                  )}
                </div>
              </div>

              {engineStatus && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-4 border-t">
                  <div>
                    <div className="text-sm text-gray-500">Daily Trades</div>
                    <div className="text-lg font-bold">
                      {engineStatus.daily_trade_count} / {engineStatus.max_daily_trades}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Analysis Interval</div>
                    <div className="text-lg font-bold">
                      {Math.floor(engineStatus.analysis_interval_seconds / 60)}m
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Monitored Symbols</div>
                    <div className="text-lg font-bold">
                      {engineStatus.monitored_symbols.length}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Today's Decisions</div>
                    <div className="text-lg font-bold">
                      {recentActivity?.total_decisions_today || 0}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Manual Analysis */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Manual Analysis
              </CardTitle>
              <CardDescription>
                Trigger AI analysis for a specific stock symbol
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Input
                  placeholder="Enter stock symbol (e.g., AAPL)"
                  value={manualSymbol}
                  onChange={(e) => setManualSymbol(e.target.value.toUpperCase())}
                  onKeyPress={(e) => e.key === 'Enter' && executeManualAnalysis()}
                  className="flex-1"
                />
                <Button 
                  onClick={executeManualAnalysis} 
                  disabled={manualAnalysisLoading || !manualSymbol.trim()}
                >
                  {manualAnalysisLoading ? (
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <TrendingUp className="h-4 w-4 mr-2" />
                  )}
                  Analyze
                </Button>
              </div>
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
                <CardTitle className="text-lg">Recent AI Decisions</CardTitle>
                <CardDescription>Latest AI trading recommendations</CardDescription>
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
                        {decision.reasoning?.substring(0, 100)}...
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
                <CardTitle className="text-lg">Recent Trades (24h)</CardTitle>
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

          {/* Monitored Symbols */}
          {engineStatus && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Currently Monitored Symbols</CardTitle>
                <CardDescription>Stocks being monitored by the AI trading engine</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {engineStatus.monitored_symbols.map((symbol) => (
                    <Badge key={symbol} variant="secondary">
                      {symbol}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AutomatedTradingControlTabs;
