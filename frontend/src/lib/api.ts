// API client for Flask backend
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';

export interface Recommendation {
  date: string;
  room_type: string;
  arrangement?: string | null;
  recommended_arr: number;
  recommended_occupancy: number;
  is_holiday: boolean;
  is_fasting?: boolean;
  is_school_holiday?: boolean;
  is_event?: boolean;
  is_weekend: boolean;
  day_of_week: string;
  // Holiday details from backend
  holiday_details?: {
    name: string;
    kind: string;
  } | null;
  // New transparent driver fields (if backend uses predictions.csv)
  is_bridge?: boolean;
  holiday_duration?: number;
  days_of_holiday?: number;
  distance_to_holiday?: number;
  // Deprecated (backend no longer sends these; keep optional for compatibility)
  considerations?: string[];
  confidence?: 'High' | 'Medium' | 'Low';
}

export interface RecommendationsResponse {
  recommendations: Recommendation[];
  count: number;
  date_range: string;
  room_type: string;
}

export interface CalendarData {
  [date: string]: Recommendation[];
}

export interface CalendarResponse {
  year: number;
  month: number;
  calendar_data: CalendarData;
}

export interface RefreshResponse {
  success: boolean;
  last_refresh?: string;
  message: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
        credentials: 'include', // Include cookies for authentication
        ...options,
      });

      if (!response.ok) {
        // Handle authentication errors
        if (response.status === 401) {
          // Redirect to login if not already there
          if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
        }
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API call failed for ${endpoint}:`, error);
      throw error;
    }
  }

  async getRecommendations(
    startDate: string,
    endDate: string,
    roomType: string = 'All'
  ): Promise<RecommendationsResponse> {
    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
      room_type: roomType,
    });

    return this.fetchApi<RecommendationsResponse>(`/api/recommendations?${params}`);
  }

  async getCalendarData(year: number, month: number): Promise<CalendarData> {
    return this.fetchApi<CalendarData>(`/api/calendar/${year}/${month}`);
  }

  async refreshData(): Promise<RefreshResponse> {
    return this.fetchApi<RefreshResponse>('/api/refresh', {
      method: 'POST',
    });
  }

  async getRoomTypes(): Promise<{ room_types: string[] }> {
    return this.fetchApi<{ room_types: string[] }>('/api/room_types');
  }
}

export const apiClient = new ApiClient();
