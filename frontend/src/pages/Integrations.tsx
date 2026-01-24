import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { integrationsApi } from '../services/api'
import { Link as LinkIcon, RefreshCw, CheckCircle, XCircle, X } from 'lucide-react'

const platforms = [
  {
    id: 'openlibrary',
    name: 'Open Library',
    description: 'Search and import books from Open Library (Free, no API key required)',
    icon: '📖',
    color: 'bg-blue-500',
    available: true,
    deprecated: false,
  },
  {
    id: 'google_books',
    name: 'Google Books',
    description: 'Search and import books from Google Books (Free, API key optional)',
    icon: '🔍',
    color: 'bg-red-500',
    available: true,
    deprecated: false,
  },
]

export default function Integrations() {
  const queryClient = useQueryClient()
  const [showConnectModal, setShowConnectModal] = useState(false)
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null)
  const [syncResult, setSyncResult] = useState<any>(null)

  const { data: connectedAccounts } = useQuery({
    queryKey: ['integrations'],
    queryFn: () => integrationsApi.get().then(res => res.data),
  })

  const connectMutation = useMutation({
    mutationFn: ({ platform, data }: { platform: string; data: any }) =>
      integrationsApi.connect(platform, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integrations'] })
      setShowConnectModal(false)
      setSyncResult({
        platform: 'connected',
        message: 'Connected successfully!'
      })
      setTimeout(() => setSyncResult(null), 5000)
    },
    onError: (error: any) => {
      console.error('Connection error:', error)
      // Error will be displayed in the modal
    },
  })

  const syncMutation = useMutation({
    mutationFn: (platform: string) => integrationsApi.sync(platform),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['integrations'] })
      queryClient.invalidateQueries({ queryKey: ['books'] })
      queryClient.invalidateQueries({ queryKey: ['preferences'] })
      setSyncResult(data.data)
      setTimeout(() => setSyncResult(null), 8000)
    },
    onError: (error: any) => {
      setSyncResult({
        platform: 'error',
        error: error?.response?.data?.detail || error?.message || 'Sync failed'
      })
      setTimeout(() => setSyncResult(null), 8000)
    },
  })

  const disconnectMutation = useMutation({
    mutationFn: (platform: string) =>
      integrationsApi.disconnect(platform),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['integrations'] })
      setSyncResult({
        platform: 'disconnected',
        message: data.data?.message || 'Disconnected successfully'
      })
      setTimeout(() => setSyncResult(null), 5000)
    },
    onError: (error: any) => {
      setSyncResult({
        platform: 'error',
        error: error?.response?.data?.detail || error?.message || 'Disconnect failed'
      })
      setTimeout(() => setSyncResult(null), 8000)
    },
  })

  const isConnected = (platformId: string) => {
    return connectedAccounts?.some((acc: any) => acc.platform === platformId)
  }

  const getLastSync = (platformId: string) => {
    const account = connectedAccounts?.find((acc: any) => acc.platform === platformId)
    return account?.last_synced_at
  }

  const handleConnect = (platformId: string) => {
    setSelectedPlatform(platformId)
    setShowConnectModal(true)
  }

  const handleConnectSubmit = () => {
    // For other platforms, you'd handle OAuth flow here
    alert(`${selectedPlatform} connection not yet implemented`)
  }

  const handleDisconnect = (platformId: string) => {
    const platformName = platforms.find(p => p.id === platformId)?.name || platformId
    
    if (!confirm(`Disconnect ${platformName}?`)) {
      return
    }
    
    disconnectMutation.mutate(platformId)
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Integrations</h1>
        <p className="mt-2 text-gray-600">Connect your reading platforms to sync data</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {platforms.map((platform) => {
          const connected = isConnected(platform.id)
          const lastSync = getLastSync(platform.id)

          return (
            <div
              key={platform.id}
              className="bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow"
            >
              <div className={`${platform.color} p-6 text-white`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-4xl mb-2">{platform.icon}</div>
                    <h3 className="text-xl font-semibold">{platform.name}</h3>
                  </div>
                  {connected ? (
                    <CheckCircle className="h-6 w-6" />
                  ) : (
                    <XCircle className="h-6 w-6 opacity-50" />
                  )}
                </div>
              </div>

              <div className="p-6">
                <p className="text-sm text-gray-600 mb-4">{platform.description}</p>
                
                {platform.deprecated && (
                  <div className="mb-4 p-2 bg-yellow-100 border border-yellow-300 rounded text-xs text-yellow-800">
                    ⚠️ This service is deprecated
                  </div>
                )}

                {!platform.available && !platform.deprecated && (
                  <div className="mb-4 p-2 bg-gray-100 border border-gray-300 rounded text-xs text-gray-600">
                    Coming soon
                  </div>
                )}

                {(platform.id === 'openlibrary' || platform.id === 'google_books') && (
                  <div className="mb-4 p-2 bg-green-100 border border-green-300 rounded text-xs text-green-800">
                    ✅ Available - Use "Add Book" page to search
                  </div>
                )}

                {connected ? (
                  <div className="space-y-3">
                    {lastSync && (
                      <p className="text-xs text-gray-500">
                        Last synced: {new Date(lastSync).toLocaleDateString()}
                      </p>
                    )}
                    {syncResult && syncResult.platform === platform.id && (
                      <div className="p-2 bg-green-100 border border-green-300 rounded text-xs text-green-800">
                        ✅ Synced: {syncResult.books_synced || 0} books, {syncResult.ratings_synced || 0} ratings
                      </div>
                    )}
                    {syncResult && syncResult.platform === 'error' && (syncMutation.isError || disconnectMutation.isError) && (
                      <div className="p-2 bg-red-100 border border-red-300 rounded text-xs text-red-800">
                        <div className="font-semibold mb-1">❌ Error</div>
                        <div className="whitespace-pre-line mb-2">{syncResult.error || 'Operation failed'}</div>
                      </div>
                    )}
                    <button
                      onClick={() => syncMutation.mutate(platform.id)}
                      disabled={syncMutation.isPending || !platform.available}
                      className="w-full bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {syncMutation.isPending ? (
                        <>
                          <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                          Syncing...
                        </>
                      ) : (
                        <>
                          <RefreshCw className="h-4 w-4 mr-2" />
                          Sync Now
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => handleDisconnect(platform.id)}
                      disabled={disconnectMutation.isPending}
                      className="w-full border border-red-300 text-red-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                    >
                      {disconnectMutation.isPending ? (
                        <>
                          <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                          Disconnecting...
                        </>
                      ) : (
                        <>
                          <X className="h-4 w-4 mr-2" />
                          Disconnect
                        </>
                      )}
                    </button>
                    {disconnectMutation.isError && syncResult?.platform === 'error' && (
                      <div className="mt-2 p-2 bg-red-100 border border-red-300 rounded text-xs text-red-800">
                        ❌ {syncResult.error || 'Disconnect failed'}
                      </div>
                    )}
                  </div>
                ) : (
                  <button 
                    onClick={() => handleConnect(platform.id)}
                    disabled={!platform.available || platform.deprecated}
                    className="w-full bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <LinkIcon className="h-4 w-4 mr-2" />
                    {platform.deprecated ? 'Deprecated' : platform.available ? 'Connect' : 'Coming Soon'}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <div className="mt-8 space-y-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-2">About Integrations</h3>
          <p className="text-sm text-blue-800">
            Connect your reading platforms to automatically sync your books, ratings, and reading history.
            This helps us provide better recommendations based on your complete reading profile.
          </p>
        </div>

      </div>

      {/* Connect Modal */}
      {showConnectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">
                Connect {platforms.find(p => p.id === selectedPlatform)?.name}
              </h2>
              <button
                onClick={() => {
                  setShowConnectModal(false)
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <p className="text-gray-600">
              Connection for {selectedPlatform} is not yet implemented.
            </p>

            <div className="mt-6 flex gap-3">
              <button
                onClick={() => {
                  setShowConnectModal(false)
                }}
                className="flex-1 border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConnectSubmit}
                disabled={connectMutation.isPending}
                className="flex-1 bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {connectMutation.isPending ? 'Connecting...' : 'Connect'}
              </button>
            </div>

            {connectMutation.isError && (
              <div className="mt-4 p-3 bg-red-100 border border-red-300 rounded text-sm text-red-800">
                <div className="font-semibold mb-2">Connection Failed</div>
                <div className="whitespace-pre-line">
                  {(connectMutation.error as any)?.response?.data?.detail || (connectMutation.error as any)?.message || 'Failed to connect'}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

