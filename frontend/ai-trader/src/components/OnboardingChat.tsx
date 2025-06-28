import React, { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { onboardingApi, type ChatMessage, type UserPreferences } from '../services/api';
import { MessageCircle, Send, Bot, User, CheckCircle } from 'lucide-react';

interface OnboardingChatProps {
  onComplete: (preferences: UserPreferences) => void;
}

export const OnboardingChat: React.FC<OnboardingChatProps> = ({ onComplete }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [extractedPreferences, setExtractedPreferences] = useState<UserPreferences | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Start with initial greeting
    const initialMessage: ChatMessage = {
      role: 'assistant',
      content: "Hello! I'm your AI investment advisor. I'm here to help you set up your investment preferences so we can provide personalized recommendations. Let's start by getting to know your investment experience. Are you new to investing, or do you have some experience with stocks and trading?",
      timestamp: new Date().toISOString()
    };
    setMessages([initialMessage]);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async () => {
    if (!currentMessage.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: currentMessage,
      timestamp: new Date().toISOString()
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setCurrentMessage('');
    setIsLoading(true);

    try {
      const response = await onboardingApi.chat({
        message: currentMessage,
        conversation_history: messages
      });

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);

      if (response.is_complete && response.preferences) {
        setIsComplete(true);
        setExtractedPreferences(response.preferences);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: "I'm sorry, I'm experiencing some technical difficulties. Please try again in a moment.",
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleCompleteOnboarding = async () => {
    if (!extractedPreferences) return;

    try {
      await onboardingApi.savePreferences(extractedPreferences);
      onComplete(extractedPreferences);
    } catch (error) {
      console.error('Error saving preferences:', error);
    }
  };

  const formatMessage = (content: string) => {
    return content.split('\n').map((line, index) => (
      <React.Fragment key={index}>
        {line}
        {index < content.split('\n').length - 1 && <br />}
      </React.Fragment>
    ));
  };

  const renderPreferenceSummary = () => {
    if (!extractedPreferences) return null;

    return (
      <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
        <div className="flex items-center gap-2 mb-3">
          <CheckCircle className="w-5 h-5 text-green-600" />
          <h3 className="font-semibold text-green-800">Onboarding Complete!</h3>
        </div>
        <div className="space-y-2 text-sm">
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">Risk: {extractedPreferences.risk_tolerance}</Badge>
            <Badge variant="secondary">Experience: {extractedPreferences.experience_level}</Badge>
            <Badge variant="secondary">Horizon: {extractedPreferences.time_horizon}-term</Badge>
            <Badge variant="secondary">Budget: {extractedPreferences.budget_range}</Badge>
          </div>
          {extractedPreferences.investment_goals.length > 0 && (
            <div>
              <span className="font-medium">Goals: </span>
              {extractedPreferences.investment_goals.join(', ')}
            </div>
          )}
          {extractedPreferences.sectors_of_interest.length > 0 && (
            <div>
              <span className="font-medium">Interested sectors: </span>
              {extractedPreferences.sectors_of_interest.join(', ')}
            </div>
          )}
        </div>
        <Button onClick={handleCompleteOnboarding} className="mt-3 w-full">
          Start Trading
        </Button>
      </div>
    );
  };

  return (
    <Card className="h-[600px] flex flex-col p-0 shadow-lg">
      <CardHeader
  className="bg-gradient-to-r from-blue-800 to-purple-400 text-white p-4 rounded-t-2xl"
>
  <CardTitle className="flex items-center gap-2 text-lg font-semibold mb-6">
    <MessageCircle className="w-8 h-8" />
    Investment Preferences Setup
  </CardTitle>
</CardHeader>
      
      <CardContent className="flex-1 flex flex-col p-4 overflow-hidden">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto mb-4 space-y-4 break-words">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex gap-3 ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.role === 'assistant' && (
                <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-white" />
                </div>
              )}
              
              <div
                className={`max-w-[80%] p-3 rounded-lg break-words ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white ml-auto'
                    : 'bg-gray-100 text-gray-800'
                }`}
                style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}
              >
                <div className="text-sm">
                  {formatMessage(message.content)}
                </div>
                {message.timestamp && (
                  <div className={`text-xs mt-1 opacity-70`}>
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                )}
              </div>
              
              {message.role === 'user' && (
                <div className="w-8 h-8 bg-gray-500 rounded-full flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
          ))}
          
          {isLoading && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className="bg-gray-100 p-3 rounded-lg">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Preferences Summary */}
        {isComplete && renderPreferenceSummary()}

        {/* Input Area */}
        {!isComplete && (
          <div className="flex gap-2">
            <Input
              value={currentMessage}
              onChange={(e) => setCurrentMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your response..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={isLoading || !currentMessage.trim()}
              size="icon"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
