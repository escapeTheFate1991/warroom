"use client";

import { useState, useEffect } from "react";
import { 
  Calendar, 
  Plus, 
  Filter, 
  Phone, 
  Mail, 
  User, 
  Clock, 
  CheckCircle2, 
  Circle,
  FileText,
  Users,
  AlertCircle,
  Search
} from "lucide-react";
import ActivityForm from "./ActivityForm";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface Activity {
  id: number;
  title: string;
  type: string;
  comment: string | null;
  schedule_from: string | null;
  schedule_to: string | null;
  is_done: boolean;
  location: string | null;
  person?: { id: number; name: string };
  deal?: { id: number; title: string };
  created_at: string;
}

export default function ActivitiesPanel() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [upcomingActivities, setUpcomingActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(false);
  const [showActivityForm, setShowActivityForm] = useState(false);
  const [filters, setFilters] = useState({
    type: "",
    isDone: "",
    dateRange: "",
    search: "",
  });

  useEffect(() => {
    fetchActivities();
    fetchUpcomingActivities();
  }, []);

  const fetchActivities = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.type) params.append('type', filters.type);
      if (filters.isDone) params.append('is_done', filters.isDone);
      if (filters.search) params.append('search', filters.search);
      
      const response = await fetch(`${API}/api/crm/activities?${params}`);
      if (response.ok) {
        const data = await response.json();
        setActivities(data);
      }
    } catch (error) {
      console.error("Failed to fetch activities:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchUpcomingActivities = async () => {
    try {
      const response = await fetch(`${API}/api/crm/activities/upcoming`);
      if (response.ok) {
        const data = await response.json();
        setUpcomingActivities(data);
      }
    } catch (error) {
      console.error("Failed to fetch upcoming activities:", error);
    }
  };

  const toggleActivityDone = async (activityId: number, isDone: boolean) => {
    try {
      const response = await fetch(`${API}/api/crm/activities/${activityId}/done`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_done: isDone }),
      });
      if (response.ok) {
        setActivities(activities.map(a => 
          a.id === activityId ? { ...a, is_done: isDone } : a
        ));
        setUpcomingActivities(upcomingActivities.map(a => 
          a.id === activityId ? { ...a, is_done: isDone } : a
        ));
      }
    } catch (error) {
      console.error("Failed to update activity:", error);
    }
  };

  const handleActivityCreated = (newActivity: Activity) => {
    setActivities([newActivity, ...activities]);
    setShowActivityForm(false);
    // Refresh upcoming if the new activity is scheduled
    if (newActivity.schedule_from) {
      fetchUpcomingActivities();
    }
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case "call": return <Phone size={16} className="text-blue-400" />;
      case "meeting": return <Users size={16} className="text-green-400" />;
      case "email": return <Mail size={16} className="text-purple-400" />;
      case "note": return <FileText size={16} className="text-gray-400" />;
      case "task": return <AlertCircle size={16} className="text-orange-400" />;
      case "lunch": return <User size={16} className="text-yellow-400" />;
      default: return <Clock size={16} className="text-gray-400" />;
    }
  };

  const formatDateTime = (dateTime: string | null) => {
    if (!dateTime) return "";
    const date = new Date(dateTime);
    return date.toLocaleDateString() + " " + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const isUpcoming = (activity: Activity) => {
    if (!activity.schedule_from) return false;
    const now = new Date();
    const scheduledTime = new Date(activity.schedule_from);
    return scheduledTime > now && !activity.is_done;
  };

  const isOverdue = (activity: Activity) => {
    if (!activity.schedule_from || activity.is_done) return false;
    const now = new Date();
    const scheduledTime = new Date(activity.schedule_from);
    return scheduledTime < now;
  };

  // Apply filters to activities
  const filteredActivities = activities.filter(activity => {
    if (filters.type && activity.type !== filters.type) return false;
    if (filters.isDone === "true" && !activity.is_done) return false;
    if (filters.isDone === "false" && activity.is_done) return false;
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      return (
        activity.title.toLowerCase().includes(searchLower) ||
        (activity.comment || "").toLowerCase().includes(searchLower) ||
        (activity.person?.name || "").toLowerCase().includes(searchLower) ||
        (activity.deal?.title || "").toLowerCase().includes(searchLower)
      );
    }
    return true;
  });

  return (
    <div className="h-full bg-[#0d1117] text-gray-200">
      {/* Header */}
      <div className="border-b border-[#30363d] p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Calendar size={24} />
            Activities
          </h1>
          <button
            onClick={() => setShowActivityForm(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2 transition"
          >
            <Plus size={16} />
            Add Activity
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search activities..."
              value={filters.search}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
              className="w-full pl-10 pr-4 py-2 bg-[#161b22] border border-[#30363d] rounded-lg text-gray-200 placeholder-gray-400 focus:outline-none focus:border-blue-400"
            />
          </div>

          <select
            value={filters.type}
            onChange={(e) => setFilters(prev => ({ ...prev, type: e.target.value }))}
            className="bg-[#161b22] border border-[#30363d] rounded-lg px-3 py-2 text-gray-200 focus:outline-none focus:border-blue-400"
            style={{ colorScheme: "dark" }}
          >
            <option value="">All Types</option>
            <option value="call">Calls</option>
            <option value="meeting">Meetings</option>
            <option value="email">Emails</option>
            <option value="note">Notes</option>
            <option value="task">Tasks</option>
            <option value="lunch">Lunch</option>
          </select>

          <select
            value={filters.isDone}
            onChange={(e) => setFilters(prev => ({ ...prev, isDone: e.target.value }))}
            className="bg-[#161b22] border border-[#30363d] rounded-lg px-3 py-2 text-gray-200 focus:outline-none focus:border-blue-400"
            style={{ colorScheme: "dark" }}
          >
            <option value="">All Status</option>
            <option value="false">Pending</option>
            <option value="true">Completed</option>
          </select>

          <button
            onClick={fetchActivities}
            className="p-2 text-gray-400 hover:text-gray-200 transition"
            title="Apply Filters"
          >
            <Filter size={16} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6">
        {/* Upcoming Activities */}
        {upcomingActivities.length > 0 && (
          <div className="mb-8">
            <h2 className="text-lg font-semibold mb-4 text-blue-400">Upcoming Activities</h2>
            <div className="space-y-3">
              {upcomingActivities.map((activity) => (
                <div key={`upcoming-${activity.id}`} className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                  <div className="flex items-start gap-3">
                    <button
                      onClick={() => toggleActivityDone(activity.id, !activity.is_done)}
                      className="mt-1 text-gray-400 hover:text-blue-400 transition"
                    >
                      {activity.is_done ? (
                        <CheckCircle2 size={18} className="text-green-400" />
                      ) : (
                        <Circle size={18} />
                      )}
                    </button>
                    
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        {getActivityIcon(activity.type)}
                        <span className="font-medium text-gray-200">{activity.title}</span>
                        <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded-full capitalize">
                          {activity.type}
                        </span>
                        {isOverdue(activity) && (
                          <span className="text-xs px-2 py-0.5 bg-red-500/20 text-red-400 rounded-full">
                            Overdue
                          </span>
                        )}
                      </div>
                      
                      {activity.comment && (
                        <p className="text-sm text-gray-300 mb-2">{activity.comment}</p>
                      )}
                      
                      <div className="flex items-center gap-4 text-xs text-gray-400">
                        {activity.schedule_from && (
                          <span className="font-medium text-blue-400">
                            {formatDateTime(activity.schedule_from)}
                          </span>
                        )}
                        {activity.location && (
                          <span>📍 {activity.location}</span>
                        )}
                        {activity.person && (
                          <span>👤 {activity.person.name}</span>
                        )}
                        {activity.deal && (
                          <span>💼 {activity.deal.title}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* All Activities */}
        <div>
          <h2 className="text-lg font-semibold mb-4">All Activities</h2>
          
          {loading ? (
            <div className="text-center py-8 text-gray-400">Loading activities...</div>
          ) : filteredActivities.length === 0 ? (
            <div className="text-center py-8 text-gray-400">No activities found</div>
          ) : (
            <div className="space-y-3">
              {filteredActivities.map((activity) => (
                <div key={activity.id} className={`p-4 border rounded-lg ${
                  activity.is_done
                    ? "bg-[#0d1117] border-[#30363d] opacity-75"
                    : isOverdue(activity)
                    ? "bg-red-500/5 border-red-500/20"
                    : "bg-[#161b22] border-[#30363d]"
                }`}>
                  <div className="flex items-start gap-3">
                    <button
                      onClick={() => toggleActivityDone(activity.id, !activity.is_done)}
                      className="mt-1 text-gray-400 hover:text-blue-400 transition"
                    >
                      {activity.is_done ? (
                        <CheckCircle2 size={18} className="text-green-400" />
                      ) : (
                        <Circle size={18} />
                      )}
                    </button>
                    
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        {getActivityIcon(activity.type)}
                        <span className={`font-medium ${activity.is_done ? "text-gray-400 line-through" : "text-gray-200"}`}>
                          {activity.title}
                        </span>
                        <span className="text-xs px-2 py-0.5 bg-gray-700 text-gray-300 rounded-full capitalize">
                          {activity.type}
                        </span>
                        {isOverdue(activity) && (
                          <span className="text-xs px-2 py-0.5 bg-red-500/20 text-red-400 rounded-full">
                            Overdue
                          </span>
                        )}
                      </div>
                      
                      {activity.comment && (
                        <p className={`text-sm mb-2 ${activity.is_done ? "text-gray-400" : "text-gray-300"}`}>
                          {activity.comment}
                        </p>
                      )}
                      
                      <div className="flex items-center justify-between text-xs text-gray-400">
                        <div className="flex items-center gap-4">
                          {activity.schedule_from && (
                            <span>{formatDateTime(activity.schedule_from)}</span>
                          )}
                          {activity.location && (
                            <span>📍 {activity.location}</span>
                          )}
                          {activity.person && (
                            <span>👤 {activity.person.name}</span>
                          )}
                          {activity.deal && (
                            <span>💼 {activity.deal.title}</span>
                          )}
                        </div>
                        <span>Created {new Date(activity.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Activity Form Modal */}
      <ActivityForm
        isOpen={showActivityForm}
        onClose={() => setShowActivityForm(false)}
        onActivityCreated={handleActivityCreated}
      />
    </div>
  );
}