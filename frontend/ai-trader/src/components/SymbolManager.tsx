import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { tradingApi } from '../services/api';
import { 
  Plus, 
  Settings, 
  TrendingUp, 
  AlertCircle,
  CheckCircle,
  X
} from 'lucide-react';

interface SymbolData {
  symbols: string[];
  count: number;
}

const SymbolManager: React.FC = () => {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [newSymbol, setNewSymbol] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isEngineRunning, setIsEngineRunning] = useState(false);

  useEffect(() => {
    loadSymbols();
    checkEngineStatus();
  }, []);

  const loadSymbols = async () => {
    try {
      const response = await fetch('/api/automated-trading/symbols');
      if (response.ok) {
        const data: SymbolData = await response.json();
        setSymbols(data.symbols);
      } else {
        setError('Failed to load symbols');
      }
    } catch (error) {
      setError('Error loading symbols');
      console.error('Error loading symbols:', error);
    }
  };

  const checkEngineStatus = async () => {
    try {
      const response = await fetch('/api/automated-trading/status');
      if (response.ok) {
        const data = await response.json();
        setIsEngineRunning(data.is_running);
      }
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

  const addSymbol = async () => {
    if (!newSymbol.trim()) return;
    
    const symbolToAdd = newSymbol.trim().toUpperCase();
    
    // Check if symbol already exists
    if (symbols.includes(symbolToAdd)) {
      setError(`Symbol ${symbolToAdd} is already in the list`);
      return;
    }
    
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      // Validate symbol first
      const isValid = await validateSymbol(symbolToAdd);
      if (!isValid) {
        setError(`Invalid symbol: ${symbolToAdd}. Please check the symbol and try again.`);
        setLoading(false);
        return;
      }

      const response = await fetch(`/api/automated-trading/symbols/add?symbol=${encodeURIComponent(symbolToAdd)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data: SymbolData = await response.json();
        setSymbols(data.symbols);
        setNewSymbol('');
        setSuccess(`Symbol ${symbolToAdd} added successfully`);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to add symbol');
      }
    } catch (error) {
      setError('Error adding symbol');
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
      const response = await fetch(`/api/automated-trading/symbols/${symbol}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        const data: SymbolData = await response.json();
        setSymbols(data.symbols);
        setSuccess(`Symbol ${symbol} removed successfully`);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to remove symbol');
      }
    } catch (error) {
      setError('Error removing symbol');
      console.error('Error removing symbol:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateAllSymbols = async (newSymbols: string[]) => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      const response = await fetch('/api/automated-trading/symbols', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newSymbols),
      });
      
      if (response.ok) {
        const data: SymbolData = await response.json();
        setSymbols(data.symbols);
        setSuccess('Symbols updated successfully');
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update symbols');
      }
    } catch (error) {
      setError('Error updating symbols');
      console.error('Error updating symbols:', error);
    } finally {
      setLoading(false);
    }
  };

  const clearMessages = () => {
    setError(null);
    setSuccess(null);
  };

  // Default popular stock symbols
  const popularSymbols = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'BRK.B',
    'V', 'JNJ', 'WMT', 'JPM', 'PG', 'UNH', 'HD', 'MA', 'DIS', 'ADBE',
    'NFLX', 'CRM', 'XOM', 'VZ', 'ABBV', 'KO', 'PEP', 'TMO', 'COST', 'AVGO'
  ];

  const addPopularSymbol = (symbol: string) => {
    if (!symbols.includes(symbol)) {
      setNewSymbol(symbol);
    }
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
            Manage the stock symbols monitored by the AI trading engine
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Status Alert */}
          {isEngineRunning && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                The trading engine is currently running. Stop the engine to modify symbols.
              </AlertDescription>
            </Alert>
          )}

          {/* Success/Error Messages */}
          {error && (
            <Alert variant="destructive">
              <X className="h-4 w-4" />
              <AlertDescription className="flex items-center justify-between">
                {error}
                <Button variant="ghost" size="sm" onClick={clearMessages}>
                  <X className="h-4 w-4" />
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
                  <X className="h-4 w-4" />
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {/* Add Symbol */}
          <div className="flex gap-2">
            <Input
              placeholder="Enter stock symbol (e.g., AAPL)"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
              onKeyPress={(e) => e.key === 'Enter' && addSymbol()}
              disabled={isEngineRunning || loading}
              className="flex-1"
            />
            <Button 
              onClick={addSymbol} 
              disabled={isEngineRunning || loading || !newSymbol.trim()}
              className="bg-blue-600 hover:bg-blue-700"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Symbol
            </Button>
          </div>

          {/* Current Symbols */}
          <div>
            <h4 className="text-sm font-medium mb-3">
              Current Symbols ({symbols.length})
            </h4>
            <div className="flex flex-wrap gap-2">
              {symbols.map((symbol) => (
                <Badge key={symbol} variant="secondary" className="flex items-center gap-2 px-3 py-1">
                  <TrendingUp className="h-3 w-3" />
                  {symbol}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeSymbol(symbol)}
                    disabled={isEngineRunning || loading || symbols.length <= 1}
                    className="h-4 w-4 p-0 hover:bg-red-100"
                  >
                    <X className="h-3 w-3 text-red-500" />
                  </Button>
                </Badge>
              ))}
            </div>
            {symbols.length === 0 && (
              <div className="text-center py-4 text-gray-500">
                No symbols configured
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Popular Symbols */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Popular Symbols</CardTitle>
          <CardDescription>
            Quick-add popular stock symbols to your monitoring list
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {popularSymbols.map((symbol) => (
              <Button
                key={symbol}
                variant={symbols.includes(symbol) ? "secondary" : "outline"}
                size="sm"
                onClick={() => addPopularSymbol(symbol)}
                disabled={isEngineRunning || symbols.includes(symbol)}
                className="text-xs"
              >
                {symbols.includes(symbol) ? (
                  <>
                    <CheckCircle className="h-3 w-3 mr-1" />
                    {symbol}
                  </>
                ) : (
                  <>
                    <Plus className="h-3 w-3 mr-1" />
                    {symbol}
                  </>
                )}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Bulk Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Bulk Actions</CardTitle>
          <CardDescription>
            Preset symbol configurations for different trading strategies
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <Button
              variant="outline"
              onClick={() => updateAllSymbols(['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'])}
              disabled={isEngineRunning || loading}
              className="text-sm"
            >
              Tech Giants
            </Button>
            <Button
              variant="outline"
              onClick={() => updateAllSymbols(['SPY', 'QQQ', 'IWM', 'VTI', 'VOO'])}
              disabled={isEngineRunning || loading}
              className="text-sm"
            >
              ETFs
            </Button>
            <Button
              variant="outline"
              onClick={() => updateAllSymbols(['JPM', 'BAC', 'WFC', 'C', 'GS'])}
              disabled={isEngineRunning || loading}
              className="text-sm"
            >
              Banking
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SymbolManager;
