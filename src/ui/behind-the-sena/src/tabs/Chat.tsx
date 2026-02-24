import React, { useEffect, useRef, useState } from "react";
import { TabLayout } from "../components/TabLayout";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Loader, User, Bot, Sparkles } from "lucide-react";
import { fetchJson } from "../utils/api";

type ChatMessage = {
  id: string;
  role: "user" | "sena";
  timestamp: string;
  content: string;
};

type ChatSession = {
  id: string;
  title: string;
  messages: ChatMessage[];
};

const CHAT_HISTORY_KEY = "sena-chat-history";
const CHAT_SESSIONS_KEY = "sena-chat-sessions";
const CHAT_ACTIVE_KEY = "sena-chat-active-session";
const defaultMessage: ChatMessage = {
  id: "1",
  role: "sena",
  timestamp: new Date().toLocaleTimeString(),
  content: "Hello! I'm Sena. How can I assist you today?",
};

export const Chat: React.FC = () => {
  const normalizeSessions = (items: ChatSession[]) => {
    return items.map((session, index) => {
      const expectedId = `session-${index + 1}`;
      if (
        session.id.startsWith("session-") &&
        session.id.split("-").length === 2
      ) {
        return { ...session, title: session.title || `Session ${index + 1}` };
      }
      return {
        ...session,
        id: expectedId,
        title: session.title || `Session ${index + 1}`,
      };
    });
  };

  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    try {
      const stored = localStorage.getItem(CHAT_SESSIONS_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as ChatSession[];
        if (Array.isArray(parsed) && parsed.length > 0) {
          return normalizeSessions(parsed);
        }
      }

      const legacy = localStorage.getItem(CHAT_HISTORY_KEY);
      if (legacy) {
        const parsed = JSON.parse(legacy) as ChatMessage[];
        if (Array.isArray(parsed) && parsed.length > 0) {
          return normalizeSessions([
            { id: "session-1", title: "Session 1", messages: parsed },
          ]);
        }
      }
    } catch (error) {
      console.warn("Failed to load chat history from storage:", error);
    }
    return normalizeSessions([
      { id: "session-1", title: "Session 1", messages: [defaultMessage] },
    ]);
  });
  const [activeSessionId, setActiveSessionId] = useState<string>(() => {
    return localStorage.getItem(CHAT_ACTIVE_KEY) || "session-1";
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeSession =
    sessions.find((session) => session.id === activeSessionId) || sessions[0];
  const messages = activeSession?.messages ?? [];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, activeSessionId]);

  useEffect(() => {
    try {
      const trimmedSessions = sessions.map((session) => ({
        ...session,
        messages: session.messages.slice(-200),
      }));
      localStorage.setItem(CHAT_SESSIONS_KEY, JSON.stringify(trimmedSessions));
      localStorage.setItem(CHAT_ACTIVE_KEY, activeSessionId);
    } catch (error) {
      console.warn("Failed to persist chat history:", error);
    }
  }, [sessions, activeSessionId]);

  useEffect(() => {
    if (
      !sessions.find((session) => session.id === activeSessionId) &&
      sessions.length > 0
    ) {
      setActiveSessionId(sessions[0].id);
    }
  }, [sessions, activeSessionId]);

  const createSession = () => {
    const nextIndex = sessions.length + 1;
    const newSession: ChatSession = {
      id: `session-${nextIndex}`,
      title: `Session ${nextIndex}`,
      messages: [defaultMessage],
    };
    setSessions((prev) => [...prev, newSession]);
    setActiveSessionId(newSession.id);
  };

  async function sendMessage() {
    if (!input.trim()) return;

    const timestamp = new Date().toLocaleTimeString();

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      timestamp,
      content: input,
    };

    setSessions((prev) =>
      prev.map((session) =>
        session.id === activeSession.id
          ? { ...session, messages: [...session.messages, userMsg] }
          : session,
      ),
    );
    setInput("");
    setLoading(true);

    try {
      const data = await fetchJson<{
        response?: string;
        message?: string;
        content?: string;
      }>("/api/v1/chat", {
        method: "POST",
        body: { message: input, session_id: activeSession.id },
      });

      const senaMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "sena",
        timestamp: new Date().toLocaleTimeString(),
        content: data.response || data.message || data.content || "No response",
      };

      setSessions((prev) =>
        prev.map((session) =>
          session.id === activeSession.id
            ? { ...session, messages: [...session.messages, senaMsg] }
            : session,
        ),
      );
    } catch (e) {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "sena",
        timestamp: new Date().toLocaleTimeString(),
        content: `Error: ${e instanceof Error ? e.message : String(e)}`,
      };
      setSessions((prev) =>
        prev.map((session) =>
          session.id === activeSession.id
            ? { ...session, messages: [...session.messages, errorMsg] }
            : session,
        ),
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <TabLayout>
      {/* Header */}
      <div className="border-b border-slate-800/50 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto w-full flex items-center gap-3 px-6 py-4">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-50">
              Chat with Sena
            </h2>
            <p className="text-xs text-slate-400">AI Assistant</p>
          </div>
        </div>
        <div className="max-w-3xl mx-auto w-full flex items-center gap-2 px-6 pb-4">
          <div className="flex items-center gap-2 overflow-x-auto">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => setActiveSessionId(session.id)}
                className={`px-3 py-1 rounded-full text-xs border transition whitespace-nowrap ${
                  activeSessionId === session.id
                    ? "bg-purple-500/20 text-purple-200 border-purple-500/40"
                    : "bg-slate-900/70 text-slate-400 border-slate-800 hover:text-slate-200"
                }`}
              >
                {session.title}
              </button>
            ))}
          </div>
          <button
            onClick={createSession}
            className="ml-auto px-3 py-1 rounded-full text-xs border border-slate-800 text-slate-300 hover:text-white hover:border-slate-600 transition"
          >
            New
          </button>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto w-full px-6 py-6 space-y-6">
          <AnimatePresence initial={false}>
            {messages.map((msg, index) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
                className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {/* Avatar (Sena) */}
                {msg.role === "sena" && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
                    className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center flex-shrink-0 shadow-lg"
                  >
                    <Bot className="w-5 h-5 text-white" />
                  </motion.div>
                )}

                {/* Message Bubble */}
                <div
                  className={`flex flex-col max-w-[75%] ${msg.role === "user" ? "items-end" : "items-start"}`}
                >
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className={`px-5 py-3 rounded-2xl shadow-lg ${
                      msg.role === "user"
                        ? "bg-gradient-to-br from-purple-600 to-purple-700 text-white rounded-tr-sm"
                        : "bg-slate-800/80 backdrop-blur-sm text-slate-100 border border-slate-700/50 rounded-tl-sm overflow-hidden"
                    }`}
                  >
                    {msg.role === "sena" ? (
                      <div className="chat-markdown text-sm">
                        <ReactMarkdown
                          components={{
                            code({ className, children, ...props }) {
                              const match = /language-(\w+)/.exec(
                                className || "",
                              );
                              const language = match?.[1];
                              if (language) {
                                return (
                                  <div className="chat-code-block">
                                    <SyntaxHighlighter
                                      {...props}
                                      style={vscDarkPlus}
                                      language={language}
                                      PreTag="div"
                                      wrapLongLines
                                      customStyle={{
                                        background: "transparent",
                                        margin: 0,
                                        padding: 0,
                                        overflowX: "hidden",
                                      }}
                                      codeTagProps={{
                                        style: {
                                          whiteSpace: "pre-wrap",
                                          wordBreak: "break-word",
                                        },
                                      }}
                                    >
                                      {String(children).replace(/\n$/, "")}
                                    </SyntaxHighlighter>
                                  </div>
                                );
                              }
                              return (
                                <code className={className} {...props}>
                                  {children}
                                </code>
                              );
                            },
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">
                        {msg.content}
                      </p>
                    )}
                  </motion.div>
                  <span className="text-[10px] text-slate-500 mt-1.5 px-2">
                    {msg.timestamp}
                  </span>
                </div>

                {/* Avatar (User) */}
                {msg.role === "user" && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
                    className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-lg"
                  >
                    <User className="w-5 h-5 text-white" />
                  </motion.div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Loading Indicator */}
          {loading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-4 items-start"
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center flex-shrink-0">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="px-5 py-3 rounded-2xl rounded-tl-sm bg-slate-800/80 backdrop-blur-sm border border-slate-700/50">
                <div className="flex gap-1.5">
                  <motion.div
                    animate={{ scale: [1, 1.3, 1] }}
                    transition={{ repeat: Infinity, duration: 1, delay: 0 }}
                    className="w-2 h-2 bg-purple-400 rounded-full"
                  />
                  <motion.div
                    animate={{ scale: [1, 1.3, 1] }}
                    transition={{ repeat: Infinity, duration: 1, delay: 0.2 }}
                    className="w-2 h-2 bg-purple-400 rounded-full"
                  />
                  <motion.div
                    animate={{ scale: [1, 1.3, 1] }}
                    transition={{ repeat: Infinity, duration: 1, delay: 0.4 }}
                    className="w-2 h-2 bg-purple-400 rounded-full"
                  />
                </div>
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-slate-800/50 backdrop-blur-sm bg-[#0A0E27]/80">
        <div className="max-w-3xl mx-auto w-full flex gap-3 px-6 py-4">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyUp={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
            placeholder="Type your message..."
            disabled={loading}
            className="flex-1 px-4 py-3 bg-slate-900/80 border border-slate-700/50 rounded-xl text-slate-50 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all disabled:opacity-50 backdrop-blur-sm"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-5 py-3 bg-gradient-to-br from-purple-600 to-purple-700 text-white rounded-xl hover:from-purple-700 hover:to-purple-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-purple-500/20"
          >
            {loading ? (
              <Loader className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </TabLayout>
  );
};
