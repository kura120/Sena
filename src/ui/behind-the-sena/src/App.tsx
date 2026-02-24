import React from "react";
import { HashRouter, Routes, Route } from "react-router-dom";
import {
  MessageSquare,
  Brain,
  Puzzle,
  Activity,
  FileText,
  Settings as SettingsIcon,
} from "lucide-react";
import { LoaderWindow } from "./windows/LoaderWindow";
import { SetupWindow } from "./windows/SetupWindow";
import { DashboardWindow } from "./windows/DashboardWindow";
import { WindowFrame } from "./components/WindowFrame";
import { Chat } from "./tabs/Chat";
import { Memory } from "./tabs/Memory";
import { Extensions } from "./tabs/Extensions";
import { Telemetry } from "./tabs/Telemetry";
import { Logs } from "./tabs/Logs";
import { Settings } from "./tabs/Settings";

export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/loader" element={<LoaderWindow />} />
        <Route path="/setup" element={<SetupWindow />} />
        <Route path="/dashboard" element={<DashboardWindow />} />
        <Route
          path="/chat"
          element={
            <WindowFrame
              title="Chat Interface"
              icon={MessageSquare}
              windowId="chat"
            >
              <Chat />
            </WindowFrame>
          }
        />
        <Route
          path="/memory"
          element={
            <WindowFrame title="Memory System" icon={Brain} windowId="memory">
              <Memory />
            </WindowFrame>
          }
        />
        <Route
          path="/extensions"
          element={
            <WindowFrame title="Extensions" icon={Puzzle} windowId="extensions">
              <Extensions />
            </WindowFrame>
          }
        />
        <Route
          path="/telemetry"
          element={
            <WindowFrame
              title="Telemetry & Metrics"
              icon={Activity}
              windowId="telemetry"
            >
              <Telemetry />
            </WindowFrame>
          }
        />
        <Route
          path="/logs"
          element={
            <WindowFrame title="System Logs" icon={FileText} windowId="logs">
              <Logs />
            </WindowFrame>
          }
        />
        <Route
          path="/settings"
          element={
            <WindowFrame
              title="Settings"
              icon={SettingsIcon}
              windowId="settings"
            >
              <Settings />
            </WindowFrame>
          }
        />
        <Route path="/" element={<LoaderWindow />} />
      </Routes>
    </HashRouter>
  );
}
