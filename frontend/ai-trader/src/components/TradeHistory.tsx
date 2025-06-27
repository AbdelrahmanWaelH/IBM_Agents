import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { RefreshCw, History, TrendingUp, TrendingDown } from 'lucide-react';
import { portfolioApi, type TradeHistoryItem } from '../services/api';

const TradeHistory: React.FC = () => {
  const [trades, setTrades] = useState<TradeHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadTradeHistory();
  }, []);

  const loadTradeHistory = async () => {
    setLoading(true);
    try {
      const history = await portfolioApi.getTradeHistory();
      // Sort by timestamp descending (newest first)
      const sortedTrades = history.sort((a, b) => 
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );
      setTrades(sortedTrades);
    } catch (error) {
      console.error('Failed to load trade history:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getActionIcon = (action: string) => {
    return action === 'buy' ? (
      <TrendingUp className="h-4 w-4 text-green-600" />
    ) : (
      <TrendingDown className="h-4 w-4 text-red-600" />
    );
  };

  const getActionColor = (action: string) => {
    return action === 'buy' 
      ? 'bg-green-100 text-green-800'
      : 'bg-red-100 text-red-800';
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center">
          <History className="h-5 w-5 mr-2" />
          Trade History
        </CardTitle>
        <Button variant="outline" size="sm" onClick={loadTradeHistory} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </CardHeader>
      <CardContent>
        {trades.length === 0 ? (
          <div className="text-center py-8">
            <History className="h-12 w-12 mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500">No trades executed yet</p>
            <p className="text-sm text-gray-400 mt-2">
              Your trading history will appear here once you start making trades
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date & Time</TableHead>
                <TableHead>Symbol</TableHead>
                <TableHead>Action</TableHead>
                <TableHead className="text-right">Quantity</TableHead>
                <TableHead className="text-right">Price</TableHead>
                <TableHead className="text-right">Total Value</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {trades.map((trade, index) => (
                <TableRow key={index}>
                  <TableCell>
                    <div className="text-sm">
                      {formatDate(trade.timestamp)}
                    </div>
                  </TableCell>
                  <TableCell className="font-medium">{trade.symbol}</TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      {getActionIcon(trade.action)}
                      <Badge className={getActionColor(trade.action)}>
                        {trade.action.toUpperCase()}
                      </Badge>
                    </div>
                  </TableCell>
                  <TableCell className="text-right">{trade.quantity}</TableCell>
                  <TableCell className="text-right">{formatCurrency(trade.price)}</TableCell>
                  <TableCell className="text-right font-medium">
                    {formatCurrency(trade.quantity * trade.price)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        
        {trades.length > 0 && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-sm text-gray-600">Total Trades</p>
                <p className="text-xl font-bold">{trades.length}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Buy Orders</p>
                <p className="text-xl font-bold text-green-600">
                  {trades.filter(t => t.action === 'buy').length}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Sell Orders</p>
                <p className="text-xl font-bold text-red-600">
                  {trades.filter(t => t.action === 'sell').length}
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default TradeHistory;
