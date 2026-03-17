"use client";

import { useState, useRef, useEffect } from "react";
import { X, Send, Lightbulb } from "lucide-react";
import { API, authFetch } from "@/lib/api";

interface PersonaChatModalProps {
  personaId: number;
  personaName: string;
  script: { hook: string; body: string; cta: string };
  formatSlug: string;
  onClose: () => void;
}

interface ChatMessage {
  id: string;
  type: "user" | "persona";
  content: string;
  timestamp: string;
  behavioralTrigger?: string;
  suggestedFix?: string;
}

interface PersonaResponse {
  response: string;
  behavioral_trigger: string;
  suggested_fix: string;
}

export default function PersonaChatModal({
  personaId,
  personaName,
  script,
  formatSlug,
  onClose
}: PersonaChatModalProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [personaData, setPersonaData] = useState<{
    name: string;
    archetype: string;
    avatar: string;
  } | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize chat with persona introduction based on script
  useEffect(() => {
    const initializeChat = async () => {
      setLoading(true);
      
      // Mock persona data (in real app, fetch from API)
      const mockPersonaData = {
        name: personaName,
        archetype: getPersonaArchetype(personaId),
        avatar: getPersonaInitials(personaName)
      };
      setPersonaData(mockPersonaData);

      // Send initial script to persona for reaction
      try {
        const response = await sendMessageToPersona(
          `Here's the script I'm working on:\n\nHook: "${script.hook}"\nBody: "${script.body}"\nCTA: "${script.cta}"\n\nWhat do you think? Any immediate reactions?`
        );
        
        setMessages([{
          id: "1",
          type: "persona",
          content: response.response,
          timestamp: new Date().toISOString(),
          behavioralTrigger: response.behavioral_trigger,
          suggestedFix: response.suggested_fix
        }]);
      } catch (error) {
        // Fallback initial message
        const fallbackResponse = getFallbackResponse(script, mockPersonaData.archetype);
        setMessages([{
          id: "1",
          type: "persona",
          content: fallbackResponse.response,
          timestamp: new Date().toISOString(),
          behavioralTrigger: fallbackResponse.behavioral_trigger,
          suggestedFix: fallbackResponse.suggested_fix
        }]);
      }
      
      setLoading(false);
    };

    initializeChat();
  }, [personaId, personaName, script]);

  const sendMessageToPersona = async (message: string): Promise<PersonaResponse> => {
    try {
      const response = await authFetch(`${API}/api/simulate/persona-chat`, {
        method: "POST",
        body: JSON.stringify({
          persona_id: personaId,
          user_message: message,  // API expects 'user_message' not 'message'
          script: script,
          format_slug: formatSlug,
          conversation_history: messages.map(m => ({
            role: m.type === "user" ? "user" : "assistant",
            content: m.content
          }))
        })
      });

      if (response.ok) {
        const data = await response.json();
        return {
          response: data.response || data.message || "I see what you mean...",
          behavioral_trigger: data.behavioral_trigger || "general_response",
          suggested_fix: data.suggested_fix || ""
        };
      } else {
        throw new Error("API call failed");
      }
    } catch (error) {
      // Fallback to mock response
      return generateMockResponse(message, personaData?.archetype || "casual_user");
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: "user",
      content: inputValue.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue("");
    setLoading(true);

    try {
      const response = await sendMessageToPersona(inputValue.trim());
      
      const personaMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: "persona",
        content: response.response,
        timestamp: new Date().toISOString(),
        behavioralTrigger: response.behavioral_trigger,
        suggestedFix: response.suggested_fix
      };

      setMessages(prev => [...prev, personaMessage]);
    } catch (error) {
      console.error("Failed to send message:", error);
    }
    
    setLoading(false);
    inputRef.current?.focus();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const getPersonaArchetype = (id: number): string => {
    const archetypes = [
      "casual_user", "tech_skeptic", "early_adopter", "budget_conscious", 
      "influencer", "business_owner", "content_creator", "researcher"
    ];
    return archetypes[id % archetypes.length];
  };

  const getPersonaInitials = (name: string): string => {
    return name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);
  };

  const getFallbackResponse = (script: any, archetype: string): PersonaResponse => {
    const responses: Record<string, PersonaResponse> = {
      tech_skeptic: {
        response: "Hmm, I've seen this type of hook before. The 'secret' angle feels a bit played out to me. Also, your CTA is pretty generic - 'link in bio' doesn't tell me what I'm actually going to get.",
        behavioral_trigger: "friction_points.hates_generic_ctas",
        suggested_fix: "Try a more specific CTA that explains the value: 'Get the 3-step guide in my bio' instead of just 'link in bio'"
      },
      casual_user: {
        response: "Ooh this looks interesting! I like the hook, it definitely makes me curious. But I'm wondering - how long does this actually take? I'm pretty busy so if it's super time-consuming I might skip it.",
        behavioral_trigger: "friction_points.time_concerned",
        suggested_fix: "Add a time promise to your hook: 'in just 5 minutes' or 'without spending hours'"
      },
      budget_conscious: {
        response: "Okay I'm intrigued but... how much does this cost? I hate when creators don't mention pricing upfront. Also, is there a free version or trial?",
        behavioral_trigger: "friction_points.price_sensitive",
        suggested_fix: "Address pricing concerns early: mention 'free method' or 'no credit card required' if applicable"
      },
      influencer: {
        response: "The hook has potential but it's not super shareable. I need content that my audience will want to repost or tag friends in. This feels more like a personal story than something viral.",
        behavioral_trigger: "behavior_patterns.shareability_focused",
        suggested_fix: "Make it more relatable: 'Anyone else still doing [old way]?' or add a tag-worthy element"
      }
    };

    return responses[archetype] || responses.casual_user;
  };

  const generateMockResponse = (userMessage: string, archetype: string): PersonaResponse => {
    const commonResponses = [
      {
        response: "That makes sense. I can see how that would work better. Let me think about this more...",
        behavioral_trigger: "engagement.consideration",
        suggested_fix: "Good direction - try testing this version"
      },
      {
        response: "I'm still not 100% convinced. Can you explain how this is different from what everyone else is doing?",
        behavioral_trigger: "friction_points.differentiation_unclear", 
        suggested_fix: "Add a unique angle or POV to stand out from competitors"
      },
      {
        response: "Actually, that could work! I'm starting to see the value. What would be the next step?",
        behavioral_trigger: "behavior_patterns.ready_to_act",
        suggested_fix: "Strong response - this version is connecting better"
      }
    ];

    return commonResponses[Math.floor(Math.random() * commonResponses.length)];
  };

  if (!personaData) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6">
          <div className="animate-spin w-6 h-6 border-2 border-warroom-accent border-t-transparent rounded-full mx-auto mb-3"></div>
          <p className="text-sm text-warroom-muted text-center">Loading persona...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-warroom-bg border border-warroom-border rounded-xl w-full max-w-2xl h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-warroom-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-warroom-accent/20 text-warroom-accent flex items-center justify-center font-bold">
              {personaData.avatar}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-warroom-text">{personaData.name}</h3>
              <p className="text-xs text-warroom-muted capitalize">{personaData.archetype.replace("_", " ")}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-warroom-surface rounded-lg text-warroom-muted hover:text-warroom-text transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((message) => (
            <div key={message.id} className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] ${message.type === "user" ? "order-2" : "order-1"}`}>
                {/* Message bubble */}
                <div className={`rounded-2xl px-4 py-3 ${
                  message.type === "user"
                    ? "bg-warroom-accent/20 text-warroom-text ml-4"
                    : "bg-warroom-surface text-warroom-text mr-4"
                }`}>
                  <p className="text-sm leading-relaxed">{message.content}</p>
                </div>
                
                {/* Persona-specific metadata */}
                {message.type === "persona" && message.behavioralTrigger && (
                  <div className="mt-2 mr-4">
                    <div className="bg-warroom-bg border border-warroom-border rounded-lg p-3 space-y-2">
                      <div className="flex items-center gap-2 text-xs">
                        <div className="w-2 h-2 rounded-full bg-orange-400"></div>
                        <span className="text-warroom-muted font-medium">Behavioral Trigger:</span>
                        <span className="text-orange-400 font-mono">{message.behavioralTrigger}</span>
                      </div>
                      {message.suggestedFix && (
                        <div className="bg-warroom-accent/10 border border-warroom-accent/20 rounded p-2">
                          <div className="flex items-start gap-2">
                            <Lightbulb size={12} className="text-warroom-accent mt-0.5 flex-shrink-0" />
                            <div>
                              <div className="text-xs font-medium text-warroom-accent mb-1">Suggested Fix:</div>
                              <p className="text-xs text-warroom-text leading-relaxed">{message.suggestedFix}</p>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Timestamp */}
                <div className={`text-xs text-warroom-muted mt-1 ${
                  message.type === "user" ? "text-right mr-4" : "text-left ml-4"
                }`}>
                  {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
              
              {/* Avatar for persona messages */}
              {message.type === "persona" && (
                <div className="w-8 h-8 rounded-full bg-warroom-accent/20 text-warroom-accent flex items-center justify-center text-xs font-bold order-1 mr-2 mt-1 flex-shrink-0">
                  {personaData.avatar}
                </div>
              )}
            </div>
          ))}
          
          {/* Loading indicator */}
          {loading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 bg-warroom-surface rounded-2xl px-4 py-3 mr-4">
                <div className="flex gap-1">
                  <div className="w-2 h-2 rounded-full bg-warroom-accent animate-bounce"></div>
                  <div className="w-2 h-2 rounded-full bg-warroom-accent animate-bounce" style={{ animationDelay: "0.1s" }}></div>
                  <div className="w-2 h-2 rounded-full bg-warroom-accent animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-warroom-border p-4">
          <div className="flex gap-3">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about the script, test different hooks, or get feedback..."
              rows={1}
              className="flex-1 bg-warroom-surface border border-warroom-border rounded-lg px-4 py-3 text-sm text-warroom-text resize-none focus:outline-none focus:border-warroom-accent transition-colors"
              style={{ minHeight: "44px", maxHeight: "120px" }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = "44px";
                target.style.height = Math.min(target.scrollHeight, 120) + "px";
              }}
            />
            <button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || loading}
              className="px-4 py-3 bg-warroom-accent text-white rounded-lg hover:bg-warroom-accent/80 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center"
            >
              <Send size={16} />
            </button>
          </div>
          <div className="flex justify-between items-center mt-2 text-xs text-warroom-muted">
            <span>Press Enter to send, Shift+Enter for new line</span>
            <span>Powered by Mirofish AI</span>
          </div>
        </div>
      </div>
    </div>
  );
}