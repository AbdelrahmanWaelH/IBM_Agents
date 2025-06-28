import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { OnboardingChat } from './OnboardingChat';
import { onboardingApi, type UserPreferences } from '../services/api';
import { 
  TrendingUp, 
  MessageCircle, 
  CheckCircle, 
  BarChart3, 
  Target, 
  Shield,
  Clock,
  Briefcase,
  DollarSign,
  Settings
} from 'lucide-react';

interface OnboardingPageProps {
  onComplete: () => void;
}

export const OnboardingPage: React.FC<OnboardingPageProps> = ({ onComplete }) => {
  const [showChat, setShowChat] = useState(false);
  const [existingPreferences, setExistingPreferences] = useState<UserPreferences | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkExistingPreferences();
  }, []);

  const checkExistingPreferences = async () => {
    try {
      const preferences = await onboardingApi.getPreferences();
      setExistingPreferences(preferences);
    } catch (error) {
      console.error('Error checking preferences:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartOnboarding = () => {
    setShowChat(true);
  };

  const handleSkipOnboarding = () => {
    onComplete();
  };

  const handleOnboardingComplete = (preferences: UserPreferences) => {
    setExistingPreferences(preferences);
    setTimeout(() => {
      onComplete();
    }, 2000);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (showChat) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center p-4">
        <div className="w-full max-w-4xl">
          <OnboardingChat onComplete={handleOnboardingComplete} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-3 mb-6">
            <TrendingUp className="w-12 h-12 text-blue-600" />
            <h1 className="text-4xl font-bold text-gray-800">AI Trading Agent</h1>
          </div>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Welcome to your personal AI-powered trading assistant. Let's set up your investment preferences 
            to provide you with personalized recommendations.
          </p>
        </div>

        {existingPreferences ? (
          /* Existing User Card */
          <div className="max-w-2xl mx-auto">
            <Card className="border-green-200 bg-green-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-green-800">
                  <CheckCircle className="w-6 h-6" />
                  Welcome Back!
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-green-700 mb-4">
                  We found your existing investment preferences. You can start trading right away 
                  or update your preferences if needed.
                </p>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
                  <div className="bg-white p-3 rounded-lg">
                    <div className="flex items-center gap-2 mb-1">
                      <Shield className="w-4 h-4 text-blue-600" />
                      <span className="text-sm font-medium">Risk</span>
                    </div>
                    <span className="text-sm text-gray-600 capitalize">{existingPreferences.risk_tolerance}</span>
                  </div>
                  <div className="bg-white p-3 rounded-lg">
                    <div className="flex items-center gap-2 mb-1">
                      <Clock className="w-4 h-4 text-blue-600" />
                      <span className="text-sm font-medium">Horizon</span>
                    </div>
                    <span className="text-sm text-gray-600 capitalize">{existingPreferences.time_horizon}-term</span>
                  </div>
                  <div className="bg-white p-3 rounded-lg">
                    <div className="flex items-center gap-2 mb-1">
                      <Briefcase className="w-4 h-4 text-blue-600" />
                      <span className="text-sm font-medium">Experience</span>
                    </div>
                    <span className="text-sm text-gray-600 capitalize">{existingPreferences.experience_level}</span>
                  </div>
                </div>
                <div className="flex gap-3">
                  <Button onClick={onComplete} className="flex-1">
                    Start Trading
                  </Button>
                  <Button onClick={handleStartOnboarding} variant="outline" className="flex-1">
                    Update Preferences
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          /* New User Setup */
          <div className="max-w-4xl mx-auto">
            {/* Features Grid */}
            <div className="grid md:grid-cols-3 gap-6 mb-12">
              <Card className="text-center hover:shadow-lg transition-shadow">
                <CardContent className="pt-6">
                  <BarChart3 className="w-12 h-12 text-blue-600 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Smart Analysis</h3>
                  <p className="text-gray-600">
                    AI-powered stock analysis with real-time market data and news sentiment
                  </p>
                </CardContent>
              </Card>

              <Card className="text-center hover:shadow-lg transition-shadow">
                <CardContent className="pt-6">
                  <Target className="w-12 h-12 text-green-600 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Personalized Recommendations</h3>
                  <p className="text-gray-600">
                    Tailored investment suggestions based on your risk tolerance and goals
                  </p>
                </CardContent>
              </Card>

              <Card className="text-center hover:shadow-lg transition-shadow">
                <CardContent className="pt-6">
                  <Settings className="w-12 h-12 text-purple-600 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Automated Trading</h3>
                  <p className="text-gray-600">
                    Optional automated trading with full control over your investment strategy
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Setup Options */}
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="hover:shadow-lg transition-shadow border-blue-200">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-blue-700">
                    <MessageCircle className="w-6 h-6" />
                    Personalized Setup (Recommended)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600 mb-4">
                    Chat with our AI advisor to set up your investment preferences. 
                    This takes about 3-5 minutes and ensures the best recommendations for you.
                  </p>
                  <ul className="text-sm text-gray-600 mb-6 space-y-2">
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-green-600" />
                      Determine your risk tolerance
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-green-600" />
                      Set investment goals and timeline
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-green-600" />
                      Choose preferred sectors and automation level
                    </li>
                  </ul>
                  <Button onClick={handleStartOnboarding} className="w-full">
                    Start Personalized Setup
                  </Button>
                </CardContent>
              </Card>

              <Card className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <DollarSign className="w-6 h-6" />
                    Quick Start
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600 mb-4">
                    Skip the setup and start with default settings. You can always 
                    update your preferences later in the settings.
                  </p>
                  <ul className="text-sm text-gray-600 mb-6 space-y-2">
                    <li className="flex items-center gap-2">
                      <div className="w-4 h-4 border border-gray-400 rounded"></div>
                      Moderate risk tolerance
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-4 h-4 border border-gray-400 rounded"></div>
                      Analysis-only mode
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-4 h-4 border border-gray-400 rounded"></div>
                      General investment focus
                    </li>
                  </ul>
                  <Button onClick={handleSkipOnboarding} variant="outline" className="w-full">
                    Skip Setup for Now
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
