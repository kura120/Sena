import React from 'react'
import { HashRouter, Routes, Route } from 'react-router-dom'
import { MessageSquare, Brain, Puzzle, Activity, FileText, Settings as SettingsIcon } from 'lucide-react'
import { LoaderWindow } from './windows/LoaderWindow'
import { DashboardWindow } from './windows/DashboardWindow'
import { TabWindow } from './components/TabWindow'
import { ChatTab } from './components/ChatTab'
import { MemoryTab } from './components/MemoryTab'
import { ExtensionsTab } from './components/ExtensionsTab'
import { TelemetryTab } from './components/TelemetryTab'
import { LogsTab } from './components/LogsTab'
import { SettingsTab } from './components/SettingsTab'

export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/loader" element={<LoaderWindow />} />
        <Route path="/dashboard" element={<DashboardWindow />} />
        <Route path="/chat" element={
          <TabWindow title="Chat Interface" icon={MessageSquare} windowId="chat">
            <ChatTab />
          </TabWindow>
        } />
        <Route path="/memory" element={
          <TabWindow title="Memory System" icon={Brain} windowId="memory">
            <MemoryTab />
          </TabWindow>
        } />
        <Route path="/extensions" element={
          <TabWindow title="Extensions" icon={Puzzle} windowId="extensions">
            <ExtensionsTab />
          </TabWindow>
        } />
        <Route path="/telemetry" element={
          <TabWindow title="Telemetry & Metrics" icon={Activity} windowId="telemetry">
            <TelemetryTab />
          </TabWindow>
        } />
        <Route path="/logs" element={
          <TabWindow title="System Logs" icon={FileText} windowId="logs">
            <LogsTab />
          </TabWindow>
        } />
        <Route path="/settings" element={
          <TabWindow title="Settings" icon={SettingsIcon} windowId="settings">
            <SettingsTab />
          </TabWindow>
        } />
        <Route path="/" element={<LoaderWindow />} />
      </Routes>
    </HashRouter>
  )
}