import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { tradingApi, automatedTradingApi } from '../services/api';
import { 
  Plus, 
  Settings, 
  AlertCircle,
  CheckCircle,
  X,
  Brain,
  Star,
  Zap,
  RefreshCw
} from 'lucide-react';

// interface SymbolData {
//   symbols: string[];
//   count: number;
// }

interface AIRecommendation {
  symbol: string;
  confidence: number;
  action: string;
  reasoning: string;
  current_price: number;
  change_percent: number;
}

const SymbolManager: React.FC = () => {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [newSymbol, setNewSymbol] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isEngineRunning, setIsEngineRunning] = useState(false);
  const [aiRecommendations, setAiRecommendations] = useState<AIRecommendation[]>([]);
  const [selectedRecommendations, setSelectedRecommendations] = useState<Set<string>>(new Set());
  const [mode, setMode] = useState<'predefined' | 'ai'>('predefined');

  // Predefined popular symbols with categories
  const predefinedSymbols = {
    'Tech Giants': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA'],
    'Financial': ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'V', 'MA'],
    'Consumer': ['WMT', 'PG', 'KO', 'PEP', 'NKE', 'DIS', 'HD', 'MCD'],
    'Healthcare': ['JNJ', 'PFE', 'UNH', 'ABBV', 'TMO', 'ABT', 'CVS'],
    'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD', 'MPC']
  };

  useEffect(() => {
    loadSymbols();
    checkEngineStatus();
  }, []);

  const loadSymbols = async () => {
    try {
      const data = await automatedTradingApi.getSymbols();
      setSymbols(data.symbols);
    } catch (error) {
      console.error('Error loading symbols:', error);
    }
  };

  const checkEngineStatus = async () => {
    try {
      const data = await automatedTradingApi.getStatus();
      setIsEngineRunning(data.is_running);
    } catch (error) {
      console.error('Error checking engine status:', error);
    }
  };

  const validateSymbol = async (symbol: string): Promise<boolean> => {
    try {
      await tradingApi.getStock(symbol.toUpperCase());
      return true;
    } catch {
      return false;
    }
  };

  const addSymbol = async (symbolToAdd: string) => {
    if (!symbolToAdd.trim()) return;
    
    const symbol = symbolToAdd.trim().toUpperCase();
    
    // Check if symbol already exists
    if (symbols.includes(symbol)) {
      setError(`Symbol ${symbol} is already in the list`);
      return;
    }
    
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      // Validate symbol first
      const isValid = await validateSymbol(symbol);
      if (!isValid) {
        setError(`Invalid symbol: ${symbol}. Please check the symbol and try again.`);
        setLoading(false);
        return;
      }

      const data = await automatedTradingApi.addSymbol(symbol);
      setSymbols(data.symbols);
      setNewSymbol('');
      setSuccess(`Symbol ${symbol} added successfully`);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Error adding symbol';
      setError(errorMessage);
      console.error('Error adding symbol:', error);
    } finally {
      setLoading(false);
    }
  };

  const removeSymbol = async (symbol: string) => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      const data = await automatedTradingApi.removeSymbol(symbol);
      setSymbols(data.symbols);
      setSuccess(`Symbol ${symbol} removed successfully`);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Error removing symbol';
      setError(errorMessage);
      console.error('Error removing symbol:', error);
    } finally {
      setLoading(false);
    }
  };

  const getAIRecommendations = async () => {
    setLoading(true);
    setError(null);
    setSuccess('🤖 AI is analyzing stocks using company names for better news coverage. This may take 1-2 minutes...');
    
    try {
      const data = await automatedTradingApi.getAIRecommendations(8);
      setAiRecommendations(data.recommended_stocks);
      setSuccess(`✅ AI analyzed stocks and found ${data.recommended_stocks.length} good opportunities`);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Error getting AI recommendations';
      setError(`❌ ${errorMessage}. Please ensure the backend is running and try again.`);
      console.error('Error getting AI recommendations:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleRecommendationSelection = (symbol: string) => {
    setSelectedRecommendations(prev => {
      const newSet = new Set(prev);
      if (newSet.has(symbol)) {
        newSet.delete(symbol);
      } else {
        newSet.add(symbol);
      }
      return newSet;
    });
  };

  const addSelectedAIRecommendations = async () => {
    if (selectedRecommendations.size === 0) {
      setError('Please select at least one recommendation');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);
    
    const addedSymbols = [];
    const errors = [];

    for (const symbol of Array.from(selectedRecommendations)) {
      try {
        if (!symbols.includes(symbol)) {
          await automatedTradingApi.addSymbol(symbol);
          addedSymbols.push(symbol);
        } else {
          errors.push(`${symbol}: Already in list`);
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        errors.push(`${symbol}: Error adding - ${message}`);
      }
    }

    // Reload symbols
    await loadSymbols();
    
    if (addedSymbols.length > 0) {
      setSuccess(`Added ${addedSymbols.length} symbols: ${addedSymbols.join(', ')}`);
    }
    
    if (errors.length > 0) {
      setError(`Some errors occurred: ${errors.join('; ')}`);
    }

    setSelectedRecommendations(new Set());
    setLoading(false);
  };

  const clearMessages = () => {
    setError(null);
    setSuccess(null);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Symbol Management
          </CardTitle>
          <CardDescription>
            Manage trading symbols with predefined lists or AI recommendations
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert className="mb-4">
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>{success}</AlertDescription>
            </Alert>
          )}

          {isEngineRunning && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Trading engine is running. Stop it to modify symbols.
              </AlertDescription>
            </Alert>
          )}

          <Tabs value={mode} onValueChange={(value) => setMode(value as 'predefined' | 'ai')} className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="predefined" className="flex items-center gap-2">
                <Star className="h-4 w-4" />
                Predefined Symbols
              </TabsTrigger>
              <TabsTrigger value="ai" className="flex items-center gap-2">
                <Brain className="h-4 w-4" />
                AI Recommendations
              </TabsTrigger>
            </TabsList>

            <TabsContent value="predefined" className="space-y-4">
              {/* Manual Symbol Addition */}
              <div className="flex gap-2">
                <Input
                  placeholder="Enter symbol (e.g., AAPL)"
                  value={newSymbol}
                  onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
                  onKeyPress={(e) => e.key === 'Enter' && addSymbol(newSymbol)}
                  disabled={isEngineRunning || loading}
                />
                <Button 
                  onClick={() => addSymbol(newSymbol)}
                  disabled={isEngineRunning || loading || !newSymbol.trim()}
                  className="flex items-center gap-2"
                >
                  <Plus className="h-4 w-4" />
                  Add
                </Button>
              </div>

              {/* Predefined Categories */}
              <div className="space-y-4">
                {Object.entries(predefinedSymbols).map(([category, categorySymbols]) => (
                  <div key={category}>
                    <h4 className="font-semibold mb-2">{category}</h4>
                    <div className="flex flex-wrap gap-2">
                      {categorySymbols.map((symbol) => (
                        <Button
                          key={symbol}
                          variant={symbols.includes(symbol) ? "default" : "outline"}
                          size="sm"
                          onClick={() => symbols.includes(symbol) ? removeSymbol(symbol) : addSymbol(symbol)}
                          disabled={isEngineRunning || loading}
                          className="flex items-center gap-1"
                        >
                          {symbols.includes(symbol) ? (
                            <>
                              <CheckCircle className="h-3 w-3" />
                              {symbol}
                            </>
                          ) : (
                            <>
                              <Plus className="h-3 w-3" />
                              {symbol}
                            </>
                          )}
                        </Button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="ai" className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold">AI Stock Recommendations</h4>
                  <p className="text-sm text-gray-600">Let AI analyze and recommend the best stocks to trade</p>
                </div>
                <Button 
                  onClick={getAIRecommendations}
                  disabled={loading}
                  className="flex items-center gap-2"
                >
                  {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Brain className="h-4 w-4" />}
                  Get AI Recommendations
                </Button>
              </div>

              {aiRecommendations.length > 0 && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium">Select recommendations to add:</p>
                    <Button 
                      onClick={addSelectedAIRecommendations}
                      disabled={selectedRecommendations.size === 0 || loading || isEngineRunning}
                      variant="default"
                      size="sm"
                      className="flex items-center gap-2"
                    >
                      <Zap className="h-4 w-4" />
                      Add Selected ({selectedRecommendations.size})
                    </Button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {aiRecommendations.map((rec) => (
                      <div 
                        key={rec.symbol} 
                        className={`p-3 border rounded-lg cursor-pointer transition-all ${
                          selectedRecommendations.has(rec.symbol) 
                            ? 'border-blue-500 bg-blue-50' 
                            : 'border-gray-200 hover:border-gray-300'
                        } ${symbols.includes(rec.symbol) ? 'opacity-50' : ''}`}
                        onClick={() => !symbols.includes(rec.symbol) && toggleRecommendationSelection(rec.symbol)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2">
                            <input 
                              type="checkbox"
                              checked={selectedRecommendations.has(rec.symbol)}
                              disabled={symbols.includes(rec.symbol)}
                              readOnly
                              className="mt-1"
                            />
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-semibold">{rec.symbol}</span>
                                {symbols.includes(rec.symbol) && (
                                  <Badge variant="default" className="text-xs">Already Added</Badge>
                                )}
                              </div>
                              <div className="text-sm text-gray-600">
                                ${rec.current_price.toFixed(2)} 
                                <span className={rec.change_percent >= 0 ? 'text-green-600' : 'text-red-600'}>
                                  {rec.change_percent >= 0 ? ' +' : ' '}{rec.change_percent?.toFixed(2)}%
                                </span>
                              </div>
                            </div>
                          </div>
                          <Badge variant="outline" className={
                            rec.confidence >= 0.8 ? 'bg-green-100 text-green-800' :
                            rec.confidence >= 0.6 ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }>
                            {(rec.confidence * 100).toFixed(0)}%
                          </Badge>
                        </div>
                        <p className="text-xs text-gray-500 mt-2 line-clamp-2">{rec.reasoning}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {aiRecommendations.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <Brain className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>Click "Get AI Recommendations" to let AI analyze and suggest the best stocks for trading</p>
                </div>
              )}
            </TabsContent>
          </Tabs>

          {/* Current Symbols */}
          <div className="mt-6">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold">Current Trading Symbols ({symbols.length})</h4>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={clearMessages}
                className="text-xs"
              >
                Clear Messages
              </Button>
            </div>
            
            {symbols.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {symbols.map((symbol) => (
                  <Badge 
                    key={symbol} 
                    variant="default" 
                    className="flex items-center gap-1 py-1 px-2"
                  >
                    {symbol}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeSymbol(symbol)}
                      disabled={isEngineRunning || loading}
                      className="h-4 w-4 p-0 ml-1 hover:bg-red-100"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No symbols added yet. Use the tabs above to add symbols.</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SymbolManager;