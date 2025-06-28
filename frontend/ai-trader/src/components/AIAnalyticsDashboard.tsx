import React, { useState, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { analyticsApi, type AIDecision, type TradingInsights, type SentimentSummary } from '@/services/api';
import { Brain, TrendingUp, BarChart3, CheckCircle, Clock, ArrowUp, ArrowDown, Minus } from 'lucide-react';

const AIAnalyticsDashboard: React.FC = () => {
  const [decisions, setDecisions] = useState<AIDecision[]>([]);
  const [insights, setInsights] = useState<TradingInsights | null>(null);
  const [sentiment, setSentiment] = useState<SentimentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSymbol] = useState<string>('');

  const loadAnalytics = useCallback(async () => {
    try {
      setLoading(true);
      const [decisionsData, insightsData, sentimentData] = await Promise.all([
        analyticsApi.getAIDecisions(selectedSymbol || undefined, 50),
        analyticsApi.getTradingInsights(),
        analyticsApi.getSentimentSummary(selectedSymbol || undefined)
      ]);
      
      setDecisions(decisionsData);
      setInsights(insightsData);
      setSentiment(sentimentData);
    } catch (error) {
      console.error('Error loading analytics:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedSymbol]);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  const getActionIcon = (action: string) => {
    switch (action.toLowerCase()) {
      case 'buy': return <ArrowUp className="h-4 w-4 text-green-500" />;
      case 'sell': return <ArrowDown className="h-4 w-4 text-red-500" />;
      default: return <Minus className="h-4 w-4 text-yellow-500" />;
    }
  };

  const getActionColor = (action: string) => {
    switch (action.toLowerCase()) {
      case 'buy': return 'bg-green-100 text-green-800';
      case 'sell': return 'bg-red-100 text-red-800';
      default: return 'bg-yellow-100 text-yellow-800';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="h-6 w-6 text-blue-600" />
          <h2 className="text-2xl font-bold">AI Analytics Dashboard</h2>
        </div>
        <Button onClick={loadAnalytics} variant="outline">
          Refresh Data
        </Button>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Decisions</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{insights?.total_decisions || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Confidence</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getConfidenceColor(insights?.average_confidence || 0)}`}>
              {((insights?.average_confidence || 0) * 100).toFixed(1)}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Execution Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {insights?.execution_rate.toFixed(1) || 0}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Most Recommended</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {getActionIcon(insights?.most_recommended_action || 'hold')}
              <span className="text-2xl font-bold capitalize">
                {insights?.most_recommended_action || 'Hold'}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="decisions" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="decisions">AI Decisions</TabsTrigger>
          <TabsTrigger value="sentiment">Sentiment Analysis</TabsTrigger>
          <TabsTrigger value="patterns">Trading Patterns</TabsTrigger>
        </TabsList>

        <TabsContent value="decisions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent AI Trading Decisions</CardTitle>
              <CardDescription>
                Latest AI-powered trading recommendations and their execution status
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {decisions.map((decision) => (
                  <div key={decision.id} className="border rounded-lg p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Badge className={getActionColor(decision.action)}>
                          {getActionIcon(decision.action)}
                          <span className="ml-1 capitalize">{decision.action}</span>
                        </Badge>
                        <span className="font-bold text-lg">{decision.symbol}</span>
                        <span className="text-gray-500">
                          ${decision.suggested_price.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={decision.was_executed ? "default" : "secondary"}>
                          {decision.was_executed ? (
                            <>
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Executed
                            </>
                          ) : (
                            <>
                              <Clock className="h-3 w-3 mr-1" />
                              Pending
                            </>
                          )}
                        </Badge>
                        <span className={`font-medium ${getConfidenceColor(decision.confidence)}`}>
                          {(decision.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                    <div className="text-sm text-gray-600 prose prose-sm max-w-none">
                      <ReactMarkdown>{decision.reasoning}</ReactMarkdown>
                    </div>
                    <div className="text-xs text-gray-400">
                      Created: {new Date(decision.created_at).toLocaleString()}
                    </div>
                  </div>
                ))}
                {decisions.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    No AI decisions found. Start analyzing stocks to see AI recommendations.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sentiment" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>News Sentiment Analysis</CardTitle>
              <CardDescription>
                Market sentiment based on recent news analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              {sentiment && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Card className="border-green-200">
                      <CardContent className="pt-6">
                        <div className="text-center">
                          <div className="text-3xl font-bold text-green-600">
                            {sentiment.sentiment_percentages.positive}%
                          </div>
                          <div className="text-sm text-muted-foreground">Positive</div>
                          <div className="text-xs mt-1">
                            {sentiment.sentiment_distribution.positive} articles
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                    
                    <Card className="border-yellow-200">
                      <CardContent className="pt-6">
                        <div className="text-center">
                          <div className="text-3xl font-bold text-yellow-600">
                            {sentiment.sentiment_percentages.neutral}%
                          </div>
                          <div className="text-sm text-muted-foreground">Neutral</div>
                          <div className="text-xs mt-1">
                            {sentiment.sentiment_distribution.neutral} articles
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                    
                    <Card className="border-red-200">
                      <CardContent className="pt-6">
                        <div className="text-center">
                          <div className="text-3xl font-bold text-red-600">
                            {sentiment.sentiment_percentages.negative}%
                          </div>
                          <div className="text-sm text-muted-foreground">Negative</div>
                          <div className="text-xs mt-1">
                            {sentiment.sentiment_distribution.negative} articles
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                  
                  <div className="text-center text-sm text-gray-500">
                    Based on {sentiment.total_news_items} news articles from the last {sentiment.days_analyzed} days
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="patterns" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Trading Patterns</CardTitle>
              <CardDescription>
                AI decision patterns and trading behavior analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              {insights && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="text-center p-4 border rounded-lg">
                      <div className="flex items-center justify-center gap-2 mb-2">
                        <ArrowUp className="h-5 w-5 text-green-500" />
                        <span className="font-medium">Buy Signals</span>
                      </div>
                      <div className="text-2xl font-bold text-green-600">
                        {insights.action_distribution.buy}
                      </div>
                    </div>
                    
                    <div className="text-center p-4 border rounded-lg">
                      <div className="flex items-center justify-center gap-2 mb-2">
                        <ArrowDown className="h-5 w-5 text-red-500" />
                        <span className="font-medium">Sell Signals</span>
                      </div>
                      <div className="text-2xl font-bold text-red-600">
                        {insights.action_distribution.sell}
                      </div>
                    </div>
                    
                    <div className="text-center p-4 border rounded-lg">
                      <div className="flex items-center justify-center gap-2 mb-2">
                        <Minus className="h-5 w-5 text-yellow-500" />
                        <span className="font-medium">Hold Signals</span>
                      </div>
                      <div className="text-2xl font-bold text-yellow-600">
                        {insights.action_distribution.hold}
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 border rounded-lg">
                      <h4 className="font-medium mb-2">Average Confidence</h4>
                      <div className="text-xl font-bold">
                        {(insights.average_confidence * 100).toFixed(1)}%
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        AI confidence in trading decisions
                      </p>
                    </div>
                    
                    <div className="p-4 border rounded-lg">
                      <h4 className="font-medium mb-2">Execution Rate</h4>
                      <div className="text-xl font-bold text-green-600">
                        {insights.execution_rate.toFixed(1)}%
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        Percentage of recommendations executed
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AIAnalyticsDashboard;
