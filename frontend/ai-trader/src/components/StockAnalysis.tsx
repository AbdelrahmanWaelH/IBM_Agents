import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Alert, AlertDescription } from './ui/alert';
import { Label } from './ui/label';
import { TrendingUp, TrendingDown, Minus, Brain, AlertCircle, CheckCircle, Calculator } from 'lucide-react';
import { tradingApi, type StockInfo, type TradeDecision, type TradeValidationResponse } from '../services/api';
import ReactMarkdown from 'react-markdown';

interface StockAnalysisProps {
  stock: StockInfo;
  decision: TradeDecision;
  onExecuteTrade: (decision: TradeDecision) => void;
}

const StockAnalysis: React.FC<StockAnalysisProps> = ({ stock, decision, onExecuteTrade }) => {
  const [customQuantity, setCustomQuantity] = useState<number>(decision.quantity);
  const [validation, setValidation] = useState<TradeValidationResponse | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const validateTrade = useCallback(async () => {
    if (decision.action === 'hold') return;
    
    setValidationLoading(true);
    setValidationError(null);
    
    try {
      const validationResult = await tradingApi.validateTrade({
        symbol: stock.symbol,
        action: decision.action,
        quantity: customQuantity,
        price: stock.current_price
      });
      setValidation(validationResult);
    } catch (error) {
      setValidationError('Failed to validate trade');
      console.error('Trade validation error:', error);
    } finally {
      setValidationLoading(false);
    }
  }, [decision.action, stock.symbol, stock.current_price, customQuantity]);

  // Effect to validate trade when quantity changes
  useEffect(() => {
    if (decision.action !== 'hold' && customQuantity > 0) {
      validateTrade();
    }
  }, [customQuantity, decision.action, stock.symbol, validateTrade]);

  const handleQuantityChange = (value: string) => {
    const quantity = parseInt(value) || 0;
    setCustomQuantity(quantity);
  };

  const handleExecuteTrade = () => {
    if (!validation?.valid) return;
    
    const updatedDecision = {
      ...decision,
      quantity: customQuantity,
      suggested_price: stock.current_price
    };
    
    onExecuteTrade(updatedDecision);
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

  const formatLargeNumber = (num: number) => {
    if (num >= 1e12) return `$${(num / 1e12).toFixed(1)}T`;
    if (num >= 1e9) return `$${(num / 1e9).toFixed(1)}B`;
    if (num >= 1e6) return `$${(num / 1e6).toFixed(1)}M`;
    return formatCurrency(num);
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'buy':
        return <TrendingUp className="h-4 w-4 text-green-600" />;
      case 'sell':
        return <TrendingDown className="h-4 w-4 text-red-600" />;
      default:
        return <Minus className="h-4 w-4 text-gray-600" />;
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'buy':
        return 'bg-green-100 text-green-800';
      case 'sell':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800';
    if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Stock Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            {stock.symbol}
            <Badge variant="outline" className={stock.change_percent && stock.change_percent >= 0 ? 'text-green-600' : 'text-red-600'}>
              {stock.change_percent ? formatPercent(stock.change_percent) : 'N/A'}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600">Current Price</p>
              <p className="text-xl font-bold">{formatCurrency(stock.current_price)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Market Cap</p>
              <p className="text-lg font-semibold">
                {stock.market_cap ? formatLargeNumber(stock.market_cap) : 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Volume</p>
              <p className="text-lg font-semibold">
                {stock.volume ? stock.volume.toLocaleString() : 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Day Change</p>
              <p className={`text-lg font-semibold ${
                stock.change_percent && stock.change_percent >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {stock.change_percent ? formatPercent(stock.change_percent) : 'N/A'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* AI Decision */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Brain className="h-5 w-5 mr-2 text-blue-600" />
            AI Recommendation
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              {getActionIcon(decision.action)}
              <Badge className={getActionColor(decision.action)}>
                {decision.action.toUpperCase()}
              </Badge>
            </div>
            <Badge className={getConfidenceColor(decision.confidence)}>
              {(decision.confidence * 100).toFixed(0)}% Confidence
            </Badge>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600">Suggested Quantity</p>
              <p className="text-lg font-semibold">{decision.quantity} shares</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Current Price</p>
              <p className="text-lg font-semibold">{formatCurrency(stock.current_price)}</p>
            </div>
          </div>

          <div>
            <p className="text-sm text-gray-600 mb-2">AI Reasoning</p>
            <div className="text-sm bg-gray-50 p-4 rounded-lg border max-w-none overflow-auto">
              <ReactMarkdown
                components={{
                  h1: ({ children }) => <h1 className="text-lg font-bold mb-3 text-gray-800 border-b pb-1">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-base font-semibold mb-2 text-blue-700 mt-4 flex items-center">
                    <span className="mr-2">📊</span>{children}
                  </h2>,
                  h3: ({ children }) => <h3 className="text-sm font-medium mb-2 text-gray-600 mt-3">{children}</h3>,
                  p: ({ children }) => <p className="mb-3 text-gray-700 leading-relaxed">{children}</p>,
                  ul: ({ children }) => <ul className="mb-3 ml-4 space-y-1">{children}</ul>,
                  li: ({ children }) => <li className="text-gray-700 list-disc leading-relaxed">{children}</li>,
                  strong: ({ children }) => <strong className="font-semibold text-gray-800">{children}</strong>,
                  em: ({ children }) => <em className="italic text-gray-600">{children}</em>,
                  code: ({ children }) => <code className="bg-gray-200 px-2 py-1 rounded text-xs font-mono text-gray-800">{children}</code>
                }}
              >
                {decision.reasoning}
              </ReactMarkdown>
            </div>
          </div>

          {decision.action !== 'hold' && (
            <div className="space-y-4">
              {/* Custom Quantity Input */}
              <div className="space-y-2">
                <Label htmlFor="quantity">Trade Quantity (shares)</Label>
                <Input
                  id="quantity"
                  type="number"
                  min="1"
                  value={customQuantity}
                  onChange={(e) => handleQuantityChange(e.target.value)}
                  placeholder="Enter number of shares"
                />
              </div>

              {/* Validation Messages */}
              {validationError && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{validationError}</AlertDescription>
                </Alert>
              )}

              {validation && !validation.valid && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    {validation.error}
                    {validation.max_affordable_shares && decision.action === 'buy' && (
                      <div className="mt-2">
                        <strong>Max affordable shares:</strong> {validation.max_affordable_shares}
                        <br />
                        <Button
                          variant="outline"
                          size="sm"
                          className="mt-1"
                          onClick={() => setCustomQuantity(validation.max_affordable_shares!)}
                        >
                          Use Max ({validation.max_affordable_shares})
                        </Button>
                      </div>
                    )}
                    {validation.available_shares && decision.action === 'sell' && (
                      <div className="mt-2">
                        <strong>Available shares:</strong> {validation.available_shares}
                        <br />
                        <Button
                          variant="outline"
                          size="sm"
                          className="mt-1"
                          onClick={() => setCustomQuantity(validation.available_shares!)}
                        >
                          Use Available ({validation.available_shares})
                        </Button>
                      </div>
                    )}
                  </AlertDescription>
                </Alert>
              )}

              {validation && validation.valid && (
                <Alert>
                  <CheckCircle className="h-4 w-4" />
                  <AlertDescription>
                    Trade validated successfully!
                    <div className="mt-2 text-sm">
                      <strong>Estimated cost:</strong> {formatCurrency(validation.estimated_cost || 0)}
                      {decision.action === 'buy' && validation.available_cash && (
                        <>
                          <br />
                          <strong>Available cash:</strong> {formatCurrency(validation.available_cash)}
                        </>
                      )}
                    </div>
                  </AlertDescription>
                </Alert>
              )}

              {/* Trade Execution Button */}
              <Button 
                onClick={handleExecuteTrade}
                className="w-full"
                variant={decision.action === 'buy' ? 'default' : 'destructive'}
                disabled={validationLoading || !validation?.valid}
              >
                {validationLoading ? (
                  <>
                    <Calculator className="h-4 w-4 mr-2 animate-spin" />
                    Validating...
                  </>
                ) : (
                  <>
                    Execute {decision.action.toUpperCase()} Order
                    {validation?.valid && (
                      <span className="ml-2">
                        ({customQuantity} shares @ {formatCurrency(stock.current_price)})
                      </span>
                    )}
                  </>
                )}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default StockAnalysis;
