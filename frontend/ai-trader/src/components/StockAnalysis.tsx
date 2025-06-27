import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { TrendingUp, TrendingDown, Minus, Brain } from 'lucide-react';
import type { StockInfo, TradeDecision } from '../services/api';

interface StockAnalysisProps {
  stock: StockInfo;
  decision: TradeDecision;
  onExecuteTrade: (decision: TradeDecision) => void;
}

const StockAnalysis: React.FC<StockAnalysisProps> = ({ stock, decision, onExecuteTrade }) => {
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
              <p className="text-sm text-gray-600">Suggested Price</p>
              <p className="text-lg font-semibold">{formatCurrency(decision.suggested_price)}</p>
            </div>
          </div>

          <div>
            <p className="text-sm text-gray-600 mb-2">AI Reasoning</p>
            <p className="text-sm bg-gray-50 p-3 rounded-lg">{decision.reasoning}</p>
          </div>

          {decision.action !== 'hold' && (
            <Button 
              onClick={() => onExecuteTrade(decision)}
              className="w-full"
              variant={decision.action === 'buy' ? 'default' : 'destructive'}
            >
              Execute {decision.action.toUpperCase()} Order
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default StockAnalysis;
