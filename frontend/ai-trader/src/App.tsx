import { useState, useEffect } from 'react'
import TradingDashboard from '@/components/TradingDashboard'
import { OnboardingPage } from '@/components/OnboardingPage'
import { Button } from '@/components/ui/button'
import { onboardingApi } from '@/services/api'
import { MessageCircle } from 'lucide-react'
import './App.css'

function App() {
  const [showOnboarding, setShowOnboarding] = useState(true)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    checkOnboardingStatus()
  }, [])

  const checkOnboardingStatus = async () => {
    try {
      const preferences = await onboardingApi.getPreferences()
      // If user has completed onboarding before, skip it
      if (preferences) {
        setShowOnboarding(false)
      }
    } catch (error) {
      console.error('Error checking onboarding status:', error)
      // On error, show onboarding to be safe
      setShowOnboarding(true)
    } finally {
      setIsLoading(false)
    }
  }

  const handleOnboardingComplete = () => {
    setShowOnboarding(false)
  }

  const handleShowOnboarding = () => {
    setShowOnboarding(true)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading AI Trading Agent...</p>
        </div>
      </div>
    )
  }

  if (showOnboarding) {
    return <OnboardingPage onComplete={handleOnboardingComplete} />
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">AI Trading Agent</h1>
              <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                Powered by IBM Granite
              </span>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-sm text-gray-500">
                Paper Trading Simulation
              </div>
              <Button 
                onClick={handleShowOnboarding}
                variant="outline"
                size="sm"
                className="flex items-center gap-2"
              >
                <MessageCircle className="w-4 h-4" />
                Setup Preferences
              </Button>
            </div>
          </div>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <TradingDashboard onShowOnboarding={handleShowOnboarding} />
      </main>
    </div>
  )
}

export default App
