import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { analyticsApi, type TradingInsights, type PortfolioPerformance, type SentimentSummary } from '@/services/api';
import { Brain, TrendingUp, TrendingDown, DollarSign, Activity, CheckCircle } from 'lucide-react';

const AIInsightsSummary: React.FC = () => {
  const [insights, setInsights] = useState<TradingInsights | null>(null);
  const [performance, setPerformance] = useState<PortfolioPerformance | null>(null);
  const [sentiment, setSentiment] = useState<SentimentSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSummaryData();
  }, []);

  const loadSummaryData = async () => {
    try {
      setLoading(true);
      const [insightsData, performanceData, sentimentData] = await Promise.all([
        analyticsApi.getTradingInsights(),
        analyticsApi.getPortfolioPerformance(),
        analyticsApi.getSentimentSummary(undefined, 7)
      ]);
      
      setInsights(insightsData);
      setPerformance(performanceData);
      setSentiment(sentimentData);
    } catch (error) {
      console.error('Error loading summary data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getMarketSentiment = () => {
    if (!sentiment) return { label: 'Unknown', color: 'gray', icon: Activity };
    
    const { positive, negative } = sentiment.sentiment_percentages;
    
    if (positive > 50) return { label: 'Bullish', color: 'green', icon: TrendingUp };
    if (negative > 50) return { label: 'Bearish', color: 'red', icon: TrendingDown };
    if (positive > negative) return { label: 'Optimistic', color: 'blue', icon: TrendingUp };
    if (negative > positive) return { label: 'Cautious', color: 'orange', icon: TrendingDown };
    return { label: 'Neutral', color: 'gray', icon: Activity };
  };

  const getAIConfidenceLevel = () => {
    if (!insights) return { label: 'Unknown', color: 'gray' };
    
    const confidence = insights.average_confidence * 100;
    if (confidence >= 80) return { label: 'Very High', color: 'green' };
    if (confidence >= 60) return { label: 'High', color: 'blue' };
    if (confidence >= 40) return { label: 'Moderate', color: 'yellow' };
    return { label: 'Low', color: 'red' };
  };

  const marketSentiment = getMarketSentiment();
  const aiConfidence = getAIConfidenceLevel();
  const SentimentIcon = marketSentiment.icon;

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="p-6">
              <div className="h-8 bg-gray-200 rounded mb-2"></div>
              <div className="h-4 bg-gray-200 rounded"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* AI Status Banner */}
      <Card className="border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Brain className="h-8 w-8 text-blue-600" />
              <div>
                <CardTitle className="text-xl">AI Trading System Status</CardTitle>
                <CardDescription>
                  IBM Granite-powered intelligent trading analysis
                </CardDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <span className="text-sm font-medium text-green-700">Active</span>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-green-200">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Portfolio Value</CardTitle>
            <DollarSign className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              ${performance?.portfolio_value.toLocaleString() || '0'}
            </div>
            <p className="text-xs text-muted-foreground">
              Cash: ${performance?.cash_balance.toLocaleString() || '0'}
            </p>
          </CardContent>
        </Card>

        <Card className={`border-${marketSentiment.color}-200`}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Market Sentiment</CardTitle>
            <SentimentIcon className={`h-4 w-4 text-${marketSentiment.color}-500`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold text-${marketSentiment.color}-600`}>
              {marketSentiment.label}
            </div>
            <p className="text-xs text-muted-foreground">
              {sentiment?.total_news_items || 0} articles analyzed
            </p>
          </CardContent>
        </Card>

        <Card className={`border-${aiConfidence.color}-200`}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">AI Confidence</CardTitle>
            <Brain className={`h-4 w-4 text-${aiConfidence.color}-500`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold text-${aiConfidence.color}-600`}>
              {aiConfidence.label}
            </div>
            <p className="text-xs text-muted-foreground">
              {((insights?.average_confidence || 0) * 100).toFixed(1)}% avg
            </p>
          </CardContent>
        </Card>

        <Card className="border-blue-200">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Trade Execution</CardTitle>
            <Activity className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {insights?.execution_rate.toFixed(1) || 0}%
            </div>
            <p className="text-xs text-muted-foreground">
              {performance?.total_trades || 0} total trades
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Insights */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Brain className="h-5 w-5" />
              AI Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {insights && (
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {insights.action_distribution.buy}
                  </div>
                  <div className="text-sm text-muted-foreground">Buy Signals</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">
                    {insights.action_distribution.sell}
                  </div>
                  <div className="text-sm text-muted-foreground">Sell Signals</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-yellow-600">
                    {insights.action_distribution.hold}
                  </div>
                  <div className="text-sm text-muted-foreground">Hold Signals</div>
                </div>
              </div>
            )}
            
            <div className="pt-2 border-t">
              <div className="flex justify-between items-center">
                <span className="text-sm">Most Recommended Action:</span>
                <Badge variant="outline" className="capitalize">
                  {insights?.most_recommended_action || 'Unknown'}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Sentiment Analysis
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {sentiment && (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm">Positive News</span>
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-green-500 h-2 rounded-full" 
                        style={{ width: `${sentiment.sentiment_percentages.positive}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium">{sentiment.sentiment_percentages.positive}%</span>
                  </div>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-sm">Negative News</span>
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-red-500 h-2 rounded-full" 
                        style={{ width: `${sentiment.sentiment_percentages.negative}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium">{sentiment.sentiment_percentages.negative}%</span>
                  </div>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-sm">Neutral News</span>
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-yellow-500 h-2 rounded-full" 
                        style={{ width: `${sentiment.sentiment_percentages.neutral}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium">{sentiment.sentiment_percentages.neutral}%</span>
                  </div>
                </div>
              </div>
            )}
            
            <div className="pt-2 border-t text-center">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={loadSummaryData}
                className="w-full"
              >
                Refresh Analysis
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AIInsightsSummary;
