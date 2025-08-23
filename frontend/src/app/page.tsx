'use client'

import { Terminal, MessageCircle, Settings, Activity } from 'lucide-react'

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="text-2xl">🚁</div>
            <h1 className="text-xl font-bold">ShellPilot</h1>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-sm text-slate-400">
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
              <span>Connected</span>
            </div>
            <button className="rounded-md border border-slate-700 p-2 hover:bg-slate-800">
              <Settings className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Split Layout */}
      <div className="flex h-[calc(100vh-73px)]">
        {/* Left Panel - Terminal */}
        <div className="flex-1 border-r border-slate-800 bg-slate-900">
          <div className="flex h-full flex-col">
            {/* Terminal Header */}
            <div className="border-b border-slate-800 px-4 py-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Terminal className="h-4 w-4 text-slate-400" />
                  <span className="text-sm font-medium">Terminal</span>
                </div>
                <div className="flex items-center space-x-2 text-xs text-slate-500">
                  <Activity className="h-3 w-3" />
                  <span>Session: 0m • Commands: 0</span>
                </div>
              </div>
            </div>

            {/* Terminal Content */}
            <div className="flex-1 p-4">
              <div className="h-full rounded-lg bg-slate-950 p-4 font-mono text-sm">
                <div className="mb-2 text-slate-300">Welcome to ShellPilot Terminal</div>
                <div className="mb-4 text-xs text-slate-500">
                  AI-powered Linux system administration
                </div>
                <div className="flex items-center text-slate-300">
                  <span className="text-green-400">raghav@shellpilot</span>
                  <span className="text-slate-500">:</span>
                  <span className="text-blue-400">~</span>
                  <span className="text-slate-500">$ </span>
                  <span className="ml-1 animate-pulse">_</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel - AI Chat */}
        <div className="w-96 bg-slate-900">
          <div className="flex h-full flex-col">
            {/* Chat Header */}
            <div className="border-b border-slate-800 px-4 py-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <MessageCircle className="h-4 w-4 text-slate-400" />
                  <span className="text-sm font-medium">AI Assistant</span>
                </div>
                <div className="text-xs text-slate-500">DeepSeek R1</div>
              </div>
            </div>

            {/* Chat Content */}
            <div className="flex-1 p-4">
              <div className="flex h-full flex-col space-y-4">
                {/* Welcome Message */}
                <div className="rounded-lg bg-slate-800 p-3 text-sm">
                  <div className="mb-1 font-medium text-blue-400">🤖 ShellPilot AI</div>
                  <div className="text-slate-300">
                    Hello! I'm your AI Linux assistant. What would you like to do today?
                  </div>
                </div>

                {/* Quick Actions */}
                <div className="space-y-2">
                  <div className="text-xs font-medium text-slate-400">Quick Actions</div>
                  <div className="space-y-1">
                    <button className="w-full rounded-md bg-slate-800 px-3 py-2 text-left text-xs hover:bg-slate-700">
                      Check system performance
                    </button>
                    <button className="w-full rounded-md bg-slate-800 px-3 py-2 text-left text-xs hover:bg-slate-700">
                      Install development tools
                    </button>
                    <button className="w-full rounded-md bg-slate-800 px-3 py-2 text-left text-xs hover:bg-slate-700">
                      Set up web server
                    </button>
                  </div>
                </div>

                {/* Spacer */}
                <div className="flex-1"></div>

                {/* Input Area */}
                <div className="space-y-2">
                  <input
                    type="text"
                    placeholder="Type your request here..."
                    className="w-full rounded-md bg-slate-800 border border-slate-700 px-3 py-2 text-sm placeholder-slate-500 focus:border-slate-600 focus:outline-none"
                  />
                  <div className="flex space-x-2">
                    <button className="flex-1 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium hover:bg-blue-700">
                      Send
                    </button>
                    <button className="rounded-md border border-slate-700 px-3 py-2 text-sm hover:bg-slate-800">
                      Workflow
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}