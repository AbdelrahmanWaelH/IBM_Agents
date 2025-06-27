import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { RefreshCw, TrendingUp, TrendingDown } from 'lucide-react';
import type { Portfolio } from '../services/api';

interface PortfolioOverviewProps {
  portfolio: Portfolio | null;
  onRefresh: () => void;
}

const PortfolioOverview: React.FC<PortfolioOverviewProps> = ({ portfolio, onRefresh }) => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };


  if (!portfolio) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-32">
          <p>No portfolio data available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Portfolio Summary */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Portfolio Holdings</CardTitle>
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {portfolio.holdings.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500">No holdings in your portfolio</p>
              <p className="text-sm text-gray-400 mt-2">
                Start by analyzing a stock and making your first trade
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead className="text-right">Quantity</TableHead>
                  <TableHead className="text-right">Avg Price</TableHead>
                  <TableHead className="text-right">Current Price</TableHead>
                  <TableHead className="text-right">Value</TableHead>
                  <TableHead className="text-right">P&L</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {portfolio.holdings.map((holding) => (
                  <TableRow key={holding.symbol}>
                    <TableCell className="font-medium">{holding.symbol}</TableCell>
                    <TableCell className="text-right">{holding.quantity}</TableCell>
                    <TableCell className="text-right">{formatCurrency(holding.avg_price)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(holding.current_price)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(holding.value)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end space-x-1">
                        {holding.profit_loss >= 0 ? (
                          <TrendingUp className="h-4 w-4 text-green-600" />
                        ) : (
                          <TrendingDown className="h-4 w-4 text-red-600" />
                        )}
                        <Badge 
                          variant="outline"
                          className={holding.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}
                        >
                          {formatCurrency(holding.profit_loss)}
                        </Badge>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Portfolio Allocation */}
      {portfolio.holdings.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Portfolio Allocation</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {portfolio.holdings.map((holding) => {
                const percentage = (holding.value / portfolio.total_value) * 100;
                return (
                  <div key={holding.symbol} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="font-medium min-w-16">{holding.symbol}</span>
                      <div className="flex-1 bg-gray-200 rounded-full h-2 min-w-32">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${Math.min(percentage, 100)}%` }}
                        />
                      </div>
                    </div>
                    <div className="text-right min-w-20">
                      <span className="text-sm font-medium">{percentage.toFixed(1)}%</span>
                      <div className="text-xs text-gray-500">{formatCurrency(holding.value)}</div>
                    </div>
                  </div>
                );
              })}
              
              {/* Cash allocation */}
              {portfolio.cash_balance > 0 && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="font-medium min-w-16">CASH</span>
                    <div className="flex-1 bg-gray-200 rounded-full h-2 min-w-32">
                      <div
                        className="bg-green-600 h-2 rounded-full"
                        style={{ width: `${Math.min((portfolio.cash_balance / portfolio.total_value) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                  <div className="text-right min-w-20">
                    <span className="text-sm font-medium">
                      {((portfolio.cash_balance / portfolio.total_value) * 100).toFixed(1)}%
                    </span>
                    <div className="text-xs text-gray-500">{formatCurrency(portfolio.cash_balance)}</div>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default PortfolioOverview;
