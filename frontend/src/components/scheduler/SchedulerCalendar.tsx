"use client";

import { useState, useEffect } from "react";
import {
    Calendar as CalendarIcon,
    ChevronLeft,
    ChevronRight,
    Plus,
    Filter,
    MoreHorizontal,
    Instagram,
    Youtube,
    Twitter,
    Facebook,
    Clock,
    CheckCircle2,
    CalendarDays,
    Loader2,
    Linkedin,
    Send,
    Eye,
    Edit3,
    AtSign
} from "lucide-react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { CreateContentModal } from "./CreateContentModal";
import { authFetch, API } from "@/lib/api";

const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

interface ScheduledPost {
    id: string;
    platform: string;
    content_type: string;
    caption: string;
    scheduled_for: string;
    status: string;
    media_path?: string;
    published_url?: string;
}

export default function SchedulerCalendar() {
    const [selectedDate, setSelectedDate] = useState<Date>(new Date());
    const [scheduledItems, setScheduledItems] = useState<ScheduledPost[]>([]);
    const [loading, setLoading] = useState(true);
    const [publishingId, setPublishingId] = useState<string | null>(null);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

    const fetchSchedule = async () => {
        setLoading(true);
        try {
            // Build date range for current month
            const year = selectedDate.getFullYear();
            const month = selectedDate.getMonth();
            const startDate = new Date(year, month, 1).toISOString();
            const endDate = new Date(year, month + 1, 0, 23, 59, 59).toISOString();
            
            const res = await authFetch(
                `${API}/api/scheduler/calendar?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`
            );
            const data = await res.json();
            setScheduledItems(data.posts || data.data || data || []);
        } catch (error) {
            console.error("Failed to fetch schedule", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSchedule();
    }, [selectedDate]);

    const handlePublishNow = async (item: ScheduledPost) => {
        setPublishingId(item.id);
        try {
            const response = await authFetch(`${API}/api/scheduler/posts/${item.id}/publish`, {
                method: "POST",
            });

            if (response.ok) {
                await fetchSchedule();
            } else {
                const data = await response.json();
                alert(data.error || "Failed to publish");
            }
        } catch (error) {
            console.error("Publish error", error);
        } finally {
            setPublishingId(null);
        }
    };

    // Calendar generation logic
    const startOfMonth = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1);
    const endOfMonth = new Date(selectedDate.getFullYear(), selectedDate.getMonth() + 1, 0);
    const dateOffset = startOfMonth.getDay();

    const calendarGrid = Array.from({ length: 42 }, (_, i) => {
        const date = new Date(startOfMonth);
        date.setDate(i - dateOffset + 1);

        const itemsForDate = scheduledItems.filter(item => {
            if (!item.scheduled_for) return false;
            const d = new Date(item.scheduled_for);
            return d.getDate() === date.getDate() &&
                d.getMonth() === date.getMonth() &&
                d.getFullYear() === date.getFullYear();
        });

        return {
            date,
            isCurrentMonth: date.getMonth() === selectedDate.getMonth(),
            items: itemsForDate
        };
    });

    const selectedDateItems = scheduledItems.filter(item => {
        if (!item.scheduled_for) return false;
        const d = new Date(item.scheduled_for);
        return d.getDate() === selectedDate.getDate() &&
            d.getMonth() === selectedDate.getMonth() &&
            d.getFullYear() === selectedDate.getFullYear();
    });

    const getPlatformIcon = (platform: string) => {
        switch (platform.toLowerCase()) {
            case 'instagram': return <Instagram className="h-3 w-3" />;
            case 'youtube': return <Youtube className="h-3 w-3" />;
            case 'twitter': return <Twitter className="h-3 w-3" />;
            case 'facebook': return <Facebook className="h-3 w-3" />;
            case 'linkedin': return <Linkedin className="h-3 w-3" />;
            case 'threads': return <AtSign className="h-3 w-3" />;
            default: return <CalendarIcon className="h-3 w-3" />;
        }
    };

    return (
        <div className="max-w-7xl mx-auto space-y-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl sm:text-3xl font-bold text-warroom-text tracking-tight">Content Calendar</h1>
                    <p className="text-warroom-muted mt-1 text-base sm:text-lg">Manage and schedule your AI-generated campaigns.</p>
                </div>
                <button
                    onClick={() => setIsCreateModalOpen(true)}
                    className="flex items-center gap-2 bg-warroom-accent hover:bg-warroom-accent/90 text-white px-4 sm:px-6 py-3 rounded-xl font-bold transition-all shadow-lg text-sm sm:text-base"
                >
                    <Plus className="h-4 w-4 sm:h-5 sm:w-5" />
                    <span className="hidden sm:inline">SCHEDULE NEW</span>
                    <span className="sm:hidden">NEW</span>
                </button>
            </div>

            {/* Create Content Modal */}
            <CreateContentModal
                isOpen={isCreateModalOpen}
                onClose={() => {
                    setIsCreateModalOpen(false);
                    fetchSchedule(); // Refresh schedule after creating content
                }}
            />

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                <div className="lg:col-span-1 lg:order-2 order-1">
                    <div className="bg-warroom-surface rounded-3xl p-6 h-full flex flex-col min-h-[600px] border border-warroom-border shadow-xl">
                        <div className="flex items-center justify-between mb-8 pb-4 border-b border-warroom-border">
                            <div className="flex items-center gap-3">
                                <div className="h-12 w-12 rounded-2xl bg-warroom-accent/10 flex items-center justify-center text-warroom-accent border border-warroom-accent/20">
                                    <CalendarDays className="h-6 w-6" />
                                </div>
                                <div>
                                    <h3 className="text-xl font-black text-warroom-text uppercase tracking-tighter">
                                        {selectedDate.toLocaleString('default', { month: 'short', day: 'numeric' })}
                                    </h3>
                                    <p className="text-xs text-warroom-muted font-bold">{selectedDateItems.length} Items</p>
                                </div>
                            </div>
                        </div>

                        <div className="flex-1 space-y-8 overflow-y-auto max-h-[500px] pr-2 custom-scrollbar">
                            {selectedDateItems.map(item => (
                                <motion.div 
                                    key={item.id} 
                                    className="relative group/item"
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.3 }}
                                >
                                    <div className={cn(
                                        "absolute left-0 top-0 bottom-0 w-1 rounded-full transition-all group-hover/item:w-1.5",
                                        item.status === 'published' ? 'bg-emerald-500' : 'bg-warroom-accent'
                                    )}></div>
                                    <div className="pl-6 space-y-3">
                                        <div className="flex items-center justify-between">
                                            <span className="text-[10px] font-black text-warroom-muted uppercase tracking-widest flex items-center gap-1.5">
                                                <Clock className="h-3 w-3" />
                                                {new Date(item.scheduled_for).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                            <span className={cn(
                                                "text-[10px] font-black px-2 py-0.5 rounded uppercase tracking-tighter",
                                                item.status === 'published' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-warroom-accent/10 text-warroom-accent'
                                            )}>
                                                {item.status}
                                            </span>
                                        </div>
                                        <h4 className="text-warroom-text font-bold leading-tight group-hover/item:text-warroom-accent transition-colors cursor-pointer line-clamp-2 uppercase tracking-tighter italic">
                                            {item.caption}
                                        </h4>
                                        <div className="flex items-center gap-4">
                                            <div className="flex items-center gap-1.5 text-[10px] text-warroom-muted font-black uppercase tracking-widest">
                                                {getPlatformIcon(item.platform)}
                                                <span>{item.platform}</span>
                                            </div>
                                            <span className="text-[10px] text-warroom-muted uppercase font-black tracking-tighter">{item.content_type || 'Post'}</span>
                                        </div>
                                        <div className="pt-2 flex gap-2">
                                            <button className="h-8 flex-1 bg-warroom-bg hover:bg-warroom-surface text-warroom-text rounded-lg text-[10px] font-black uppercase tracking-widest transition-all border border-warroom-border flex items-center justify-center gap-2">
                                                <Eye className="h-3 w-3" /> Preview
                                            </button>
                                            <button
                                                disabled={item.status === 'published' || publishingId === item.id}
                                                onClick={() => handlePublishNow(item)}
                                                className={cn(
                                                    "h-8 flex-1 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all border flex items-center justify-center gap-2 shadow-lg",
                                                    item.status === 'published' ? "bg-warroom-surface border-warroom-border text-warroom-muted opacity-50" : "bg-warroom-accent/20 border-warroom-accent/30 text-warroom-accent hover:bg-warroom-accent/30"
                                                )}
                                            >
                                                {publishingId === item.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />}
                                                {item.status === 'published' ? "Published" : "Publish"}
                                            </button>
                                        </div>
                                    </div>
                                </motion.div>
                            ))}

                            {selectedDateItems.length === 0 && (
                                <div className="flex-1 flex flex-col items-center justify-center text-center space-y-4 py-20 px-4">
                                    <div className="h-20 w-20 rounded-full bg-warroom-surface/30 flex items-center justify-center border border-dashed border-warroom-border">
                                        <CalendarIcon className="h-8 w-8 text-warroom-muted" />
                                    </div>
                                    <div>
                                        <p className="text-warroom-text font-bold uppercase tracking-tighter">No items today</p>
                                        <p className="text-xs text-warroom-muted mt-1">Ready to create magic?</p>
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="mt-auto pt-6 border-t border-warroom-border">
                            <div className="bg-warroom-bg rounded-2xl p-5 border border-warroom-border/50 space-y-3 shadow-2xl">
                                <p className="text-[10px] font-black text-warroom-text uppercase tracking-widest flex items-center gap-2">
                                    <CheckCircle2 className="h-3 w-3 text-emerald-500" /> Smart Flow Active
                                </p>
                                <p className="text-[10px] text-warroom-muted leading-relaxed font-medium">
                                    AI is monitoring {selectedDateItems.length} items for global peak engagement times.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="lg:col-span-3 lg:order-1 order-2 space-y-6">
                    <div className="bg-warroom-surface rounded-3xl overflow-hidden border border-warroom-border">
                        <div className="p-4 sm:p-6 border-b border-warroom-border">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                <div className="flex items-center gap-2 sm:gap-4">
                                    <h2 className="text-lg sm:text-xl font-black text-warroom-text uppercase tracking-tighter">
                                        {selectedDate.toLocaleString('default', { month: 'long', year: 'numeric' })}
                                    </h2>
                                    <div className="flex gap-1">
                                        <button
                                            onClick={() => setSelectedDate(new Date(selectedDate.setMonth(selectedDate.getMonth() - 1)))}
                                            className="h-8 w-8 rounded-lg hover:bg-warroom-surface flex items-center justify-center transition-colors text-warroom-muted"
                                        >
                                            <ChevronLeft className="h-4 w-4" />
                                        </button>
                                        <button
                                            onClick={() => setSelectedDate(new Date(selectedDate.setMonth(selectedDate.getMonth() + 1)))}
                                            className="h-8 w-8 rounded-lg hover:bg-warroom-surface flex items-center justify-center transition-colors text-warroom-muted"
                                        >
                                            <ChevronRight className="h-4 w-4" />
                                        </button>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 sm:gap-4">
                                    <div className="flex flex-wrap items-center gap-2 sm:gap-4 sm:border-r sm:border-warroom-border sm:pr-4">
                                        <div className="flex items-center gap-1.5">
                                            <div className="h-2 w-2 rounded-full bg-warroom-accent shadow-[0_0_8px_rgba(99,102,241,0.6)]"></div>
                                            <span className="text-[10px] font-bold text-warroom-muted uppercase tracking-widest">Scheduled</span>
                                        </div>
                                        <div className="flex items-center gap-1.5">
                                            <div className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]"></div>
                                            <span className="text-[10px] font-bold text-warroom-muted uppercase tracking-widest">Published</span>
                                        </div>
                                    </div>
                                    <button className="h-10 w-10 flex items-center justify-center rounded-xl bg-warroom-bg/50 border border-warroom-border text-warroom-muted hover:text-warroom-text transition-all">
                                        <Filter className="h-5 w-5" />
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-7 text-center py-4 bg-warroom-bg/30">
                            {days.map(day => (
                                <div key={day} className="text-[10px] font-black text-warroom-muted uppercase tracking-widest">{day}</div>
                            ))}
                        </div>

                        <div className="grid grid-cols-7 border-t border-warroom-border">
                            {calendarGrid.map((slot, i) => (
                                <div
                                    key={i}
                                    onClick={() => setSelectedDate(slot.date)}
                                    className={cn(
                                        "min-h-[80px] md:min-h-[140px] p-1 sm:p-2 border-r border-b border-warroom-border transition-all cursor-pointer group relative",
                                        !slot.isCurrentMonth ? "bg-warroom-bg/40 opacity-20" : "hover:bg-warroom-accent/5",
                                        slot.date.toDateString() === selectedDate.toDateString() ? "bg-warroom-accent/5" : ""
                                    )}
                                >
                                    <div className="flex justify-between items-start mb-2">
                                        <span className={cn(
                                            "text-xs font-bold h-7 w-7 flex items-center justify-center rounded-lg transition-all",
                                            slot.date.toDateString() === selectedDate.toDateString() ? "bg-warroom-accent text-white shadow-lg" : "text-warroom-muted group-hover:text-warroom-text"
                                        )}>
                                            {slot.date.getDate()}
                                        </span>
                                    </div>
                                    <div className="space-y-1">
                                        {slot.items.slice(0, 3).map(item => (
                                            <div
                                                key={item.id}
                                                className={cn(
                                                    "p-2 rounded-lg text-[10px] font-bold border flex flex-col gap-1 transition-all",
                                                    item.status === 'published'
                                                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                                                        : 'bg-warroom-accent/10 border-warroom-accent/20 text-warroom-accent shadow-sm'
                                                )}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <span className="truncate">{item.content_type || 'Post'}</span>
                                                    {getPlatformIcon(item.platform)}
                                                </div>
                                            </div>
                                        ))}
                                        {slot.items.length > 3 && (
                                            <div className="text-[8px] text-warroom-muted font-bold text-center">
                                                + {slot.items.length - 3} more
                                            </div>
                                        )}
                                    </div>
                                    {slot.date.toDateString() === new Date().toDateString() && (
                                        <div className="absolute top-2 right-2 h-1.5 w-1.5 bg-warroom-accent rounded-full animate-ping"></div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}