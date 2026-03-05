"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Calendar, ChevronLeft, ChevronRight, Clock, FileText, Loader2, Eye, X
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface DayData {
  has_memory: boolean;
  preview: string;
  size: number;
}

interface CalendarData {
  year: number;
  month: number;
  days: Record<string, DayData>;
}

interface DayDetail {
  date: string;
  content: string;
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function ActivityCalendar() {
  const [currentDate, setCurrentDate] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() + 1 };
  });
  
  const [calendarData, setCalendarData] = useState<CalendarData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  // Day detail modal
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [dayDetail, setDayDetail] = useState<DayDetail | null>(null);
  const [dayLoading, setDayLoading] = useState(false);

  // Load calendar data for current month
  const loadCalendarData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      
      const monthStr = `${currentDate.year}-${currentDate.month.toString().padStart(2, '0')}`;
      const response = await fetch(`${API}/api/calendar?month=${monthStr}`);
      
      if (!response.ok) throw new Error("Failed to load calendar data");
      
      const data = await response.json();
      setCalendarData(data);
      
    } catch (err) {
      console.error("Error loading calendar:", err);
      setError("Failed to load calendar data");
    } finally {
      setLoading(false);
    }
  }, [currentDate]);

  // Load day detail
  const loadDayDetail = async (day: string) => {
    try {
      setDayLoading(true);
      setSelectedDay(day);
      
      const response = await fetch(`${API}/api/calendar/day/${day}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          setDayDetail(null);
          return;
        }
        throw new Error("Failed to load day detail");
      }
      
      const data = await response.json();
      setDayDetail(data);
      
    } catch (err) {
      console.error("Error loading day detail:", err);
      setDayDetail(null);
    } finally {
      setDayLoading(false);
    }
  };

  // Navigate months
  const navigateMonth = (delta: number) => {
    setCurrentDate(prev => {
      let newMonth = prev.month + delta;
      let newYear = prev.year;
      
      if (newMonth > 12) {
        newMonth = 1;
        newYear += 1;
      } else if (newMonth < 1) {
        newMonth = 12;
        newYear -= 1;
      }
      
      return { year: newYear, month: newMonth };
    });
  };

  // Generate calendar grid
  const generateCalendarGrid = () => {
    if (!calendarData) return [];
    
    const firstDay = new Date(calendarData.year, calendarData.month - 1, 1);
    const lastDay = new Date(calendarData.year, calendarData.month, 0);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay()); // Start from Sunday
    
    const grid = [];
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];
    
    for (let week = 0; week < 6; week++) {
      const weekDays = [];
      for (let day = 0; day < 7; day++) {
        const date = new Date(startDate);
        date.setDate(startDate.getDate() + (week * 7) + day);
        
        const dateStr = date.toISOString().split('T')[0];
        const isCurrentMonth = date.getMonth() === calendarData.month - 1;
        const isToday = dateStr === todayStr;
        const hasMemory = calendarData.days[dateStr]?.has_memory || false;
        
        weekDays.push({
          date: date,
          dateStr: dateStr,
          day: date.getDate(),
          isCurrentMonth,
          isToday,
          hasMemory,
          memoryData: calendarData.days[dateStr]
        });
      }
      grid.push(weekDays);
    }
    
    return grid;
  };

  // Load data when month changes
  useEffect(() => {
    loadCalendarData();
  }, [loadCalendarData]);

  // Close day detail modal
  const closeDayDetail = () => {
    setSelectedDay(null);
    setDayDetail(null);
  };

  const calendarGrid = generateCalendarGrid();

  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="border-b border-warroom-border p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-warroom-text flex items-center gap-2">
              <Calendar size={20} className="text-warroom-accent" />
              Activity Calendar
            </h2>
            <p className="text-sm text-warroom-muted mt-1">
              Daily memory files and activity tracking
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigateMonth(-1)}
              className="p-2 rounded-lg bg-warroom-bg border border-warroom-border hover:bg-warroom-surface transition-colors"
            >
              <ChevronLeft size={16} />
            </button>
            
            <div className="text-center min-w-[140px]">
              <h3 className="font-semibold text-warroom-text">
                {MONTH_NAMES[currentDate.month - 1]} {currentDate.year}
              </h3>
            </div>
            
            <button
              onClick={() => navigateMonth(1)}
              className="p-2 rounded-lg bg-warroom-bg border border-warroom-border hover:bg-warroom-surface transition-colors"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
        
        {error && (
          <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </div>

      {/* Calendar Grid */}
      <div className="p-4">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={24} className="animate-spin text-warroom-accent" />
          </div>
        ) : (
          <div>
            {/* Day headers */}
            <div className="grid grid-cols-7 gap-2 mb-2">
              {DAY_NAMES.map(day => (
                <div key={day} className="text-center py-2">
                  <span className="text-xs font-medium text-warroom-muted">{day}</span>
                </div>
              ))}
            </div>
            
            {/* Calendar days */}
            <div className="space-y-2">
              {calendarGrid.map((week, weekIdx) => (
                <div key={weekIdx} className="grid grid-cols-7 gap-2">
                  {week.map((dayInfo, dayIdx) => (
                    <button
                      key={dayIdx}
                      onClick={() => dayInfo.hasMemory && loadDayDetail(dayInfo.dateStr)}
                      className={`
                        relative aspect-square rounded-lg p-2 text-sm transition-colors border
                        ${!dayInfo.isCurrentMonth 
                          ? "text-warroom-muted bg-warroom-bg/50 border-transparent cursor-default"
                          : dayInfo.hasMemory
                            ? "bg-warroom-accent/10 border-warroom-accent/30 hover:bg-warroom-accent/20 cursor-pointer"
                            : "bg-warroom-bg border-warroom-border hover:bg-warroom-surface cursor-default"
                        }
                        ${dayInfo.isToday ? "ring-2 ring-warroom-accent" : ""}
                      `}
                      disabled={!dayInfo.hasMemory}
                    >
                      <span className={`
                        font-medium
                        ${!dayInfo.isCurrentMonth 
                          ? "text-warroom-muted" 
                          : dayInfo.isToday 
                            ? "text-warroom-accent" 
                            : "text-warroom-text"
                        }
                      `}>
                        {dayInfo.day}
                      </span>
                      
                      {dayInfo.hasMemory && (
                        <div className="absolute top-1 right-1 w-2 h-2 bg-warroom-accent rounded-full" />
                      )}
                      
                      {dayInfo.hasMemory && dayInfo.memoryData && (
                        <div className="absolute bottom-1 left-1 right-1">
                          <div className="text-xs text-warroom-muted bg-warroom-bg/80 rounded px-1">
                            {Math.round(dayInfo.memoryData.size / 1024)}K
                          </div>
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Day Detail Modal */}
      {selectedDay && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-warroom-surface border border-warroom-border rounded-2xl max-w-4xl w-full max-h-[80vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-warroom-border">
              <div className="flex items-center gap-3">
                <FileText size={20} className="text-warroom-accent" />
                <div>
                  <h3 className="font-semibold text-warroom-text">
                    {new Date(selectedDay).toLocaleDateString('en-US', {
                      weekday: 'long',
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric'
                    })}
                  </h3>
                  <p className="text-sm text-warroom-muted">Daily memory file</p>
                </div>
              </div>
              
              <button
                onClick={closeDayDetail}
                className="p-2 rounded-lg bg-warroom-bg border border-warroom-border hover:bg-warroom-surface transition-colors"
              >
                <X size={16} />
              </button>
            </div>
            
            {/* Modal Content */}
            <div className="flex-1 overflow-auto p-4">
              {dayLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 size={24} className="animate-spin text-warroom-accent" />
                </div>
              ) : dayDetail ? (
                <div className="bg-warroom-bg border border-warroom-border rounded-lg p-4">
                  <pre className="text-sm text-warroom-text font-mono whitespace-pre-wrap">
                    {dayDetail.content}
                  </pre>
                </div>
              ) : (
                <div className="text-center py-12 text-warroom-muted">
                  <Eye size={24} className="mx-auto mb-2 opacity-20" />
                  <p className="text-sm">No memory data for this day</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}