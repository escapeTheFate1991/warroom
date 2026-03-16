"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Calendar, ChevronLeft, ChevronRight, Plus, Clock, Instagram, Youtube, 
  Facebook, Twitter, MoreHorizontal, Edit2, Trash2, Eye, Settings
} from "lucide-react";
import { authFetch, API } from "@/lib/api";
import LoadingState from "@/components/ui/LoadingState";

interface ScheduledPost {
  id: string;
  content: string;
  platform: string;
  scheduled_for: string;
  status: string;
  media_url?: string;
  account_username?: string;
}

interface CalendarDay {
  date: Date;
  posts: ScheduledPost[];
  isToday: boolean;
  isCurrentMonth: boolean;
}

interface OptimalTime {
  platform: string;
  hour: number;
  engagement_score: number;
  day_of_week: number;
}

const PLATFORM_CONFIG = {
  instagram: { name: "Instagram", icon: Instagram, color: "#E4405F", shortColor: "bg-pink-500" },
  tiktok: { name: "TikTok", icon: TwitterIcon, color: "#000000", shortColor: "bg-gray-900" },
  youtube: { name: "YouTube", icon: Youtube, color: "#FF0000", shortColor: "bg-red-500" },
  facebook: { name: "Facebook", icon: Facebook, color: "#1877F2", shortColor: "bg-blue-500" },
};

// Custom TikTok Icon
function TwitterIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <path d="M19.589 6.686a4.793 4.793 0 0 1-3.77-4.245V2h-3.445v13.672a2.896 2.896 0 0 1-5.201 1.743l-.002-.001.002.001a2.895 2.895 0 0 1 3.183-4.51v-3.5a6.329 6.329 0 0 0-1.183-.11C5.6 8.205 2.17 11.634 2.17 15.98c0 4.344 3.429 7.674 7.774 7.674 4.344 0 7.874-3.33 7.874-7.674V10.12a8.23 8.23 0 0 0 4.715 1.49V8.56a4.831 4.831 0 0 1-2.944-1.874z"/>
    </svg>
  );
}

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

export default function SchedulerCalendar() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [scheduledPosts, setScheduledPosts] = useState<ScheduledPost[]>([]);
  const [optimalTimes, setOptimalTimes] = useState<OptimalTime[]>([]);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [loading, setLoading] = useState(true);

  // Generate calendar grid
  const generateCalendar = useCallback((): CalendarDay[] => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());
    
    const calendar: CalendarDay[] = [];
    const today = new Date();
    
    for (let i = 0; i < 42; i++) {
      const date = new Date(startDate);
      date.setDate(startDate.getDate() + i);
      
      const postsForDay = scheduledPosts.filter(post => {
        const postDate = new Date(post.scheduled_for);
        return (
          postDate.getDate() === date.getDate() &&
          postDate.getMonth() === date.getMonth() &&
          postDate.getFullYear() === date.getFullYear()
        );
      });
      
      calendar.push({
        date: new Date(date),
        posts: postsForDay,
        isToday: date.toDateString() === today.toDateString(),
        isCurrentMonth: date.getMonth() === month
      });
    }
    
    return calendar;
  }, [currentDate, scheduledPosts]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      // TODO: Replace with actual API calls
      // const postsRes = await authFetch(`${API}/api/scheduler/calendar`);
      // const postsData = await postsRes.json();
      // setScheduledPosts(postsData.posts || []);
      
      // const timesRes = await authFetch(`${API}/api/scheduler/optimal-times`);
      // const timesData = await timesRes.json();
      // setOptimalTimes(timesData.times || []);

      // Mock data for development
      const now = new Date();
      const mockPosts: ScheduledPost[] = Array.from({ length: 15 }, (_, i) => {
        const date = new Date(now);
        date.setDate(now.getDate() + Math.floor(i / 3) - 5);
        date.setHours(9 + (i % 12), 0, 0, 0);
        
        const platforms = ["instagram", "tiktok", "youtube", "facebook"];
        const platform = platforms[i % platforms.length];
        
        return {
          id: `post_${i}`,
          content: `Sample ${PLATFORM_CONFIG[platform as keyof typeof PLATFORM_CONFIG].name} post ${i + 1}. This is scheduled content that will be posted automatically.`,
          platform,
          scheduled_for: date.toISOString(),
          status: "scheduled",
          account_username: `@${platform}_account`
        };
      });
      
      setScheduledPosts(mockPosts);
      setOptimalTimes([
        { platform: "instagram", hour: 9, engagement_score: 85, day_of_week: 1 },
        { platform: "instagram", hour: 18, engagement_score: 92, day_of_week: 1 },
        { platform: "tiktok", hour: 19, engagement_score: 88, day_of_week: 1 },
        { platform: "youtube", hour: 20, engagement_score: 79, day_of_week: 1 },
        { platform: "facebook", hour: 15, engagement_score: 73, day_of_week: 1 },
      ]);
    } catch (error) {
      console.error("Failed to load calendar data:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const navigateMonth = (direction: "prev" | "next") => {
    setCurrentDate(prev => {
      const newDate = new Date(prev);
      newDate.setMonth(prev.getMonth() + (direction === "prev" ? -1 : 1));
      return newDate;
    });
  };

  const formatTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true
    });
  };

  const calendarDays = generateCalendar();

  if (loading) {
    return <LoadingState />;
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center justify-between px-6 flex-shrink-0">
        <div className="flex items-center gap-3">
          <Calendar size={20} className="text-warroom-accent" />
          <div>
            <h2 className="text-lg font-bold">Content Scheduler</h2>
            <p className="text-[11px] text-warroom-muted -mt-0.5">
              Schedule and manage posts across all platforms
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-warroom-accent text-white text-sm font-medium hover:bg-warroom-accent/80 transition"
          >
            <Plus size={14} />
            Schedule Post
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-warroom-surface border border-warroom-border text-sm hover:border-warroom-accent/30 transition">
            <Settings size={14} />
            Settings
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden flex">
        {/* Calendar */}
        <div className="flex-1 p-6">
          {/* Calendar Header */}
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-bold">
              {MONTHS[currentDate.getMonth()]} {currentDate.getFullYear()}
            </h3>
            <div className="flex items-center gap-2">
              <button
                onClick={() => navigateMonth("prev")}
                className="p-2 rounded-lg bg-warroom-surface border border-warroom-border hover:border-warroom-accent/30 transition"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                onClick={() => setCurrentDate(new Date())}
                className="px-3 py-2 rounded-lg bg-warroom-surface border border-warroom-border text-sm hover:border-warroom-accent/30 transition"
              >
                Today
              </button>
              <button
                onClick={() => navigateMonth("next")}
                className="p-2 rounded-lg bg-warroom-surface border border-warroom-border hover:border-warroom-accent/30 transition"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7 gap-px bg-warroom-border rounded-lg overflow-hidden">
            {/* Day Headers */}
            {DAYS.map(day => (
              <div key={day} className="bg-warroom-surface p-3 text-center">
                <span className="text-xs font-medium text-warroom-muted">{day}</span>
              </div>
            ))}

            {/* Calendar Days */}
            {calendarDays.map((day, index) => (
              <div
                key={index}
                className={`bg-warroom-bg min-h-[120px] p-2 cursor-pointer hover:bg-warroom-surface/50 transition ${
                  day.isToday ? "bg-warroom-accent/5 border-2 border-warroom-accent/20" : ""
                } ${!day.isCurrentMonth ? "opacity-40" : ""}`}
                onClick={() => setSelectedDate(day.date)}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-sm font-medium ${
                    day.isToday ? "text-warroom-accent" : day.isCurrentMonth ? "text-warroom-text" : "text-warroom-muted"
                  }`}>
                    {day.date.getDate()}
                  </span>
                  {day.posts.length > 0 && (
                    <span className="text-xs px-1 py-0.5 rounded bg-warroom-accent/20 text-warroom-accent">
                      {day.posts.length}
                    </span>
                  )}
                </div>
                
                {/* Post Pills */}
                <div className="space-y-1">
                  {day.posts.slice(0, 3).map((post) => {
                    const config = PLATFORM_CONFIG[post.platform as keyof typeof PLATFORM_CONFIG];
                    return (
                      <div
                        key={post.id}
                        className={`text-xs px-2 py-1 rounded ${config.shortColor} text-white truncate`}
                        title={`${formatTime(post.scheduled_for)} - ${post.content}`}
                      >
                        {formatTime(post.scheduled_for)}
                      </div>
                    );
                  })}
                  {day.posts.length > 3 && (
                    <div className="text-xs px-2 py-1 rounded bg-warroom-muted text-white">
                      +{day.posts.length - 3} more
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sidebar */}
        <div className="w-80 border-l border-warroom-border p-6">
          {/* Optimal Times */}
          <div className="mb-6">
            <h4 className="text-sm font-bold mb-3">Optimal Posting Times</h4>
            <div className="space-y-2">
              {optimalTimes.map((time, index) => {
                const config = PLATFORM_CONFIG[time.platform as keyof typeof PLATFORM_CONFIG];
                const Icon = config.icon;
                return (
                  <div key={index} className="flex items-center justify-between p-3 bg-warroom-surface border border-warroom-border rounded-lg">
                    <div className="flex items-center gap-2">
                      <Icon size={16} style={{ color: config.color }} />
                      <span className="text-sm">{config.name}</span>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium">
                        {time.hour}:00 {time.hour >= 12 ? 'PM' : 'AM'}
                      </div>
                      <div className="text-xs text-warroom-muted">
                        {time.engagement_score}% engagement
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Upcoming Posts */}
          <div>
            <h4 className="text-sm font-bold mb-3">Upcoming Posts</h4>
            <div className="space-y-3">
              {scheduledPosts
                .filter(post => new Date(post.scheduled_for) > new Date())
                .slice(0, 5)
                .map((post) => {
                  const config = PLATFORM_CONFIG[post.platform as keyof typeof PLATFORM_CONFIG];
                  const Icon = config.icon;
                  return (
                    <div key={post.id} className="p-3 bg-warroom-surface border border-warroom-border rounded-lg">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Icon size={14} style={{ color: config.color }} />
                          <span className="text-xs text-warroom-muted">{post.account_username}</span>
                        </div>
                        <button className="opacity-0 group-hover:opacity-100">
                          <MoreHorizontal size={14} className="text-warroom-muted" />
                        </button>
                      </div>
                      <p className="text-sm line-clamp-2 mb-2">{post.content}</p>
                      <div className="flex items-center gap-2 text-xs text-warroom-muted">
                        <Clock size={12} />
                        {new Date(post.scheduled_for).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          hour: "numeric",
                          minute: "2-digit",
                          hour12: true
                        })}
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
      </div>

      {/* Add Post Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center" onClick={() => setShowAddModal(false)}>
          <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6 w-full max-w-lg mx-4" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold mb-4">Schedule New Post</h3>
            <div className="text-center py-8 text-warroom-muted">
              <Calendar size={48} className="mx-auto mb-4 opacity-50" />
              <p className="mb-4">Advanced scheduling interface coming soon!</p>
              <p className="text-sm">This will include platform selection, content editor, 
              media upload, optimal time suggestions, and bulk scheduling.</p>
            </div>
            <div className="flex justify-end gap-2">
              <button 
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 text-sm rounded-lg text-warroom-muted hover:text-warroom-text transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}