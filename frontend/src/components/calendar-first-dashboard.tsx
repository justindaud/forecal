'use client';

import React, { useState, useEffect } from 'react';
import type { DateRange } from 'react-day-picker';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { MultiSelect } from '@/components/ui/multi-select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui/accordion';
import { DateRangePicker } from '@/components/ui/date-range-picker';
import { Switch } from '@/components/ui/switch';
import { ChevronLeft, ChevronRight, RefreshCw, Calendar, Info, TrendingUp, Calculator, Grid3X3, CalendarDays, Eye, BarChart3, LogOut, User } from 'lucide-react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, addMonths, subMonths, isSameDay, startOfWeek, endOfWeek } from 'date-fns';
import { apiClient, type CalendarData, type Recommendation } from '@/lib/api';
import { formatCurrency, formatCurrencyShort, formatPercentage, getRoomTypeColor } from '@/lib/utils';
import { getStoredUser, logout } from '@/lib/auth';

interface DayRecommendations {
  date: string;
  recommendations: Recommendation[];
  isHoliday: boolean;
  holidayInfo?: {
    name: string;
    kind: string;
  };
}

type ViewMode = 'month' | 'week';

export function CalendarFirstDashboard() {
  const [currentDate, setCurrentDate] = useState(new Date(2026, 0, 1)); // Start with today
  const [calendarData, setCalendarData] = useState<CalendarData>({});
  const [calendarDataLastYear, setCalendarDataLastYear] = useState<CalendarData>({});
  const [selectedDay, setSelectedDay] = useState<DayRecommendations | null>(null);
  const [loading, setLoading] = useState(false);
  const [roomTypeFilter, setRoomTypeFilter] = useState<string[]>([]);
  const [roomTypes, setRoomTypes] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>('month');
  const [arrangementFilter, setArrangementFilter] = useState<string[]>([]);
  const [roomTypeArrangements, setRoomTypeArrangements] = useState<Record<string, { RB: boolean; RO: boolean }>>({});
  const [calcRange, setCalcRange] = useState<DateRange | undefined>(undefined);
  const [calcRoomType, setCalcRoomType] = useState<string>('All');
  const [calcArrangement, setCalcArrangement] = useState<string>('RB');
  const [currentUser, setCurrentUser] = useState(getStoredUser());

  const calcRecommendations = React.useMemo(() => {
    if (!calcRange?.from || !calcRange?.to) return [] as Recommendation[];
    console.log('calcRecommendations - calcRange:', calcRange);
    console.log('calcRecommendations - calcRoomType:', calcRoomType);
    console.log('calcRecommendations - calcArrangement:', calcArrangement);
    console.log('calcRecommendations - calendarData keys:', Object.keys(calendarData).length);
    
    const dates: string[] = [];
    let cur = new Date(calcRange.from);
    while (cur <= (calcRange.to as Date)) {
      dates.push(format(cur, 'yyyy-MM-dd'));
      cur.setDate(cur.getDate() + 1);
    }
    console.log('calcRecommendations - dates:', dates);
    
    const recs: Recommendation[] = [];
    for (const d of dates) {
      const day = calendarData[d] || [];
      console.log(`calcRecommendations - date ${d}:`, day.length, 'recommendations');
      for (const r of day) {
        const roomTypeMatch = calcRoomType === 'All' || r.room_type === calcRoomType;
        const arrangementMatch = !r.arrangement || r.arrangement === calcArrangement;
        console.log(`calcRecommendations - ${d} ${r.room_type} ${r.arrangement}: roomTypeMatch=${roomTypeMatch}, arrangementMatch=${arrangementMatch}`);
        if (roomTypeMatch && arrangementMatch) {
          recs.push(r);
        }
      }
    }
    console.log('calcRecommendations - final recs:', recs.length);
    return recs;
  }, [calendarData, calcRange?.from, calcRange?.to, calcRoomType, calcArrangement]);

  const calcRecommendationsLastYear = React.useMemo(() => {
    if (!calcRange?.from || !calcRange?.to) return [] as Recommendation[];
    console.log('calcRecommendationsLastYear - calcRange:', calcRange);
    
    const dates: string[] = [];
    let cur = new Date(calcRange.from);
    while (cur <= (calcRange.to as Date)) {
      // shift to last year
      const ly = new Date(cur);
      ly.setFullYear(ly.getFullYear() - 1);
      dates.push(format(ly, 'yyyy-MM-dd'));
      cur.setDate(cur.getDate() + 1);
    }
    console.log('calcRecommendationsLastYear - dates:', dates);
    
    const recs: Recommendation[] = [];
    for (const d of dates) {
      const day = calendarData[d] || [];
      console.log(`calcRecommendationsLastYear - date ${d}:`, day.length, 'recommendations');
      for (const r of day) {
        const roomTypeMatch = calcRoomType === 'All' || r.room_type === calcRoomType;
        const arrangementMatch = !r.arrangement || r.arrangement === calcArrangement;
        if (roomTypeMatch && arrangementMatch) {
          recs.push(r);
        }
      }
    }
    console.log('calcRecommendationsLastYear - final recs:', recs.length);
    return recs;
  }, [calendarData, calcRange?.from, calcRange?.to, calcRoomType, calcArrangement]);

  useEffect(() => {
    loadRoomTypes();
    loadCalendarData();
    loadCalendarDataLastYear();
  }, [currentDate]);

  const loadRoomTypes = async () => {
    try {
      const response = await apiClient.getRoomTypes();
      setRoomTypes(response.room_types);
    } catch (error) {
      console.error('Error loading room types:', error);
    }
  };

  const loadCalendarData = async () => {
    setLoading(true);
    try {
      const year = currentDate.getFullYear();
      const month = currentDate.getMonth() + 1;
      
      console.log(`Loading calendar data for ${year}-${month}`);
      const response = await apiClient.getCalendarData(year, month);
      console.log('Calendar response:', response);
      console.log('Calendar data keys:', Object.keys(response || {}));
      console.log('Sample data for 2024-01-01:', response?.['2024-01-01']);
      console.log('Response type:', typeof response);
      console.log('Response length:', response ? Object.keys(response).length : 0);
      
      // Merge with existing calendar data instead of replacing
      setCalendarData(prev => ({
        ...prev,
        ...(response || {})
      }));
      console.log('Calendar data merged successfully');
    } catch (error) {
      console.error('Error loading calendar data:', error);
      // Don't clear existing data on error
    } finally {
      setLoading(false);
    }
  };

  const loadCalendarDataLastYear = async () => {
    try {
      const year = currentDate.getFullYear();
      const month = currentDate.getMonth() + 1;
      const lastYear = year - 1;
      
      console.log(`Loading last year calendar data for ${lastYear}-${month}`);
      const response = await apiClient.getCalendarData(lastYear, month);
      
      // Merge with existing last year calendar data
      setCalendarDataLastYear(prev => ({
        ...prev,
        ...(response || {})
      }));
      console.log('Last year calendar data merged successfully');
    } catch (error) {
      console.error('Error loading last year calendar data:', error);
    }
  };

  const loadCalculatorData = async (range: DateRange | undefined) => {
    if (!range?.from || !range?.to) return;
    
    console.log('Loading calculator data for range:', range);
    
    try {
      // Load data for current year range
      const startYear = range.from.getFullYear();
      const endYear = range.to.getFullYear();
      
      // Load data for last year range
      const lastYearStart = new Date(range.from);
      lastYearStart.setFullYear(startYear - 1);
      const lastYearEnd = new Date(range.to);
      lastYearEnd.setFullYear(endYear - 1);
      
      const promises: Promise<any>[] = [];
      
      // Load all months needed for current year
      for (let year = startYear; year <= endYear; year++) {
        for (let month = 1; month <= 12; month++) {
          promises.push(apiClient.getCalendarData(year, month));
        }
      }
      
      // Load all months needed for last year
      for (let year = startYear - 1; year <= endYear - 1; year++) {
        for (let month = 1; month <= 12; month++) {
          promises.push(apiClient.getCalendarData(year, month));
        }
      }
      
      const responses = await Promise.all(promises);
      
      // Merge all responses into calendarData
      const mergedData: CalendarData = { ...calendarData };
      responses.forEach(response => {
        if (response) {
          Object.assign(mergedData, response);
        }
      });
      
      setCalendarData(mergedData);
      console.log('Calculator data loaded successfully');
      
    } catch (error) {
      console.error('Error loading calculator data:', error);
    }
  };

  const navigateDate = (direction: 'prev' | 'next') => {
    if (viewMode === 'month') {
      setCurrentDate(prev => direction === 'prev' ? subMonths(prev, 1) : addMonths(prev, 1));
    } else {
      setCurrentDate(prev => {
        const newDate = new Date(prev);
        newDate.setDate(newDate.getDate() + (direction === 'prev' ? -7 : 7));
        return newDate;
      });
    }
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  const handleDayClick = async (date: Date) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    
    try {
      const response = await apiClient.getRecommendations(dateStr, dateStr, 'All');
      
      // Filter by selected room types and arrangements
      let filteredRecommendations = response.recommendations;
      
      if (roomTypeFilter.length > 0) {
        filteredRecommendations = filteredRecommendations.filter(rec => roomTypeFilter.includes(rec.room_type));
      }
      
      if (arrangementFilter.length > 0) {
        filteredRecommendations = filteredRecommendations.filter(rec => arrangementFilter.includes(rec.arrangement || ''));
      }
      
      // Do not filter by arrangement switches here; always load all arrangements for the modal
      
      // Get holiday information from calendar data if available
      const dayData = calendarData[dateStr] || [];
      const holidayInfo = dayData.length > 0 && dayData[0].holiday_details 
        ? dayData[0].holiday_details 
        : null;
      
      const isHoliday = filteredRecommendations.some(rec => rec.is_holiday);
      
      setSelectedDay({
        date: dateStr,
        recommendations: filteredRecommendations,
        isHoliday,
        holidayInfo: holidayInfo || undefined
      });
    } catch (error) {
      console.error('Error loading day recommendations:', error);
    }
  };

  const getDateRange = () => {
    if (viewMode === 'month') {
      const monthStart = startOfMonth(currentDate);
      const monthEnd = endOfMonth(currentDate);
      const calendarStart = new Date(monthStart);
      calendarStart.setDate(calendarStart.getDate() - monthStart.getDay());
      const calendarEnd = new Date(monthEnd);
      calendarEnd.setDate(calendarEnd.getDate() + (6 - monthEnd.getDay()));
      return { start: calendarStart, end: calendarEnd };
    } else {
      const weekStart = startOfWeek(currentDate);
      const weekEnd = endOfWeek(currentDate);
      return { start: weekStart, end: weekEnd };
    }
  };

  const { start: calendarStart, end: calendarEnd } = getDateRange();
  const calendarDays = eachDayOfInterval({ start: calendarStart, end: calendarEnd });
  
  // Last year calendar days
  const getDateRangeLastYear = () => {
    const lastYearDate = new Date(currentDate);
    lastYearDate.setFullYear(currentDate.getFullYear() - 1);
    
    if (viewMode === 'week') {
      const weekStart = startOfWeek(lastYearDate);
      const weekEnd = endOfWeek(lastYearDate);
      return { start: weekStart, end: weekEnd };
    } else {
      const monthStart = startOfMonth(lastYearDate);
      const monthEnd = endOfMonth(lastYearDate);
      const calendarStart = startOfWeek(monthStart);
      const calendarEnd = endOfWeek(monthEnd);
      return { start: calendarStart, end: calendarEnd };
    }
  };
  
  const { start: calendarStartLastYear, end: calendarEndLastYear } = getDateRangeLastYear();
  const calendarDaysLastYear = eachDayOfInterval({ start: calendarStartLastYear, end: calendarEndLastYear });
  
  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  // Removed getCalculationMethodology and methodology dialog as they were not reflecting backend

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white sticky top-0 z-40 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl md:text-3xl font-bold">Forecast Calendar</h1>
            </div>
            <div className="flex items-center gap-4">
              {currentUser && (
                <div className="flex items-center gap-2 text-sm">
                  <User className="h-4 w-4" />
                  <span>{currentUser.name}</span>
                  <span className="text-gray-300">({currentUser.role})</span>
                </div>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={logout}
                className="flex items-center gap-2 text-black"
              >
                <LogOut className="h-4 w-4"/>
                Logout
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Controls */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2">
              {/* Navigation */}
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => navigateDate('prev')} disabled={loading}>
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="sm" onClick={goToToday} disabled={loading}>
                    Today
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => navigateDate('next')} disabled={loading}>
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
                
                <div className="text-lg font-semibold text-gray-800 min-w-[200px]">
                  {viewMode === 'month' 
                    ? format(currentDate, 'MMMM yyyy')
                    : `Week of ${format(startOfWeek(currentDate), 'MMM dd, yyyy')}`
                  }
                </div>
              </div>

              {/* View Controls */}
              <div className="flex items-center gap-3">
                {/* Month Selector */}
                <Select value={currentDate.getMonth().toString()} onValueChange={(value) => {
                  const month = parseInt(value);
                  setCurrentDate(new Date(currentDate.getFullYear(), month, 1));
                }}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Array.from({ length: 12 }, (_, i) => {
                      const date = new Date(2024, i, 1);
                      return (
                        <SelectItem key={i} value={i.toString()}>
                          {format(date, 'MMMM')}
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>

                {/* Year Selector */}
                <Select value={currentDate.getFullYear().toString()} onValueChange={(value) => {
                  const year = parseInt(value);
                  setCurrentDate(new Date(year, currentDate.getMonth(), 1));
                }}>
                  <SelectTrigger className="w-20">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="max-h-60">
                    {Array.from({ length: 3 }, (_, i) => {
                      const year = 2024 + i;
                      return (
                        <SelectItem key={year} value={year.toString()}>
                          {year}
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>

                {/* View Mode Toggle */}
                <div className="flex items-center border rounded-lg p-1">
                  <Button
                    variant={viewMode === 'month' ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => setViewMode('month')}
                    className="px-3"
                  >
                    <Grid3X3 className="h-4 w-4 mr-1" />
                    Month
                  </Button>
                  <Button
                    variant={viewMode === 'week' ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => setViewMode('week')}
                    className="px-3"
                  >
                    <CalendarDays className="h-4 w-4 mr-1" />
                    Week
                  </Button>
                </div>

                {/* Room Type Filter */}
                <MultiSelect
                  options={roomTypes}
                  selected={roomTypeFilter}
                  onChange={setRoomTypeFilter}
                  placeholder="All"
                  searchPlaceholder="Search room types..."
                  className="w-full max-w-48 min-w-24"
                />

                {/* Arrangement Filter */}
                <Select value={arrangementFilter[0] || "All"} onValueChange={(value) => setArrangementFilter(value === "All" ? [] : [value])}>
                  <SelectTrigger className="w-24">
                    <SelectValue placeholder="Arrangement" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="All">All</SelectItem>
                    <SelectItem value="RB">RB</SelectItem>
                    <SelectItem value="RO">RO</SelectItem>
                  </SelectContent>
                </Select>


              </div>
            </div>
                          {/* Calculator Accordion */}
              {/* Place it in a new row and make it full width */}
              <div className="w-full">
                <Accordion type="single" collapsible className="w-full">
                  <AccordionItem value="calculator">
                    <AccordionTrigger>
                      <div className="flex items-center gap-2 text-sm font-semibold">
                        <Calculator className="h-4 w-4" /> Calculator
                      </div>
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="grid gap-4">
                        {/* Selectors */}
                        <div className="flex flex-wrap items-end gap-3">
                          <div>
                            <h4 className="text-sm font-semibold mb-2">Room Type</h4>
                            <Select value={calcRoomType} onValueChange={setCalcRoomType}>
                              <SelectTrigger className="w-40">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent className="max-h-60">
                                <SelectItem value="All">All</SelectItem>
                                {roomTypes.map(rt => (
                                  <SelectItem key={rt} value={rt}>{rt}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div>
                            <h4 className="text-sm font-semibold mb-2">Arrangement</h4>
                            <Select value={calcArrangement} onValueChange={setCalcArrangement}>
                              <SelectTrigger className="w-28">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="RB">RB</SelectItem>
                                <SelectItem value="RO">RO</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          {/* Date Range Picker */}
                          <div>
                            <h4 className="text-sm font-semibold mb-2">Date Range</h4>
                            <DateRangePicker
                              dateRange={calcRange}
                              onDateRangeChange={(range) => {
                                console.log('DateRangePicker onDateRangeChange:', range);
                                setCalcRange(range);
                                // Load calculator data when range changes
                                loadCalculatorData(range);
                              }}
                              className="w-fit"
                              placeholder="Pick a date range"
                            />
                          </div>
                        </div>
                      </div>

                      {/* Results */}
                      <div className="mt-4 grid gap-4 md:grid-cols-3 lg:grid-cols-4">
                        <Card className="bg-gray-50">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm">Total</CardTitle>
                            <CardDescription className="text-xs">Sum over selection</CardDescription>
                          </CardHeader>
                          <CardContent className="pt-0">
                            {calcRange?.from && calcRange?.to ? (
                              <div className="text-2xl font-bold text-green-700">
                                {formatCurrency(calcRecommendations.reduce((sum, r) => sum + (r.recommended_arr || 0), 0))}
                              </div>
                            ) : (
                              <div className="text-sm text-gray-500">Select a date range.</div>
                            )}
                          </CardContent>
                        </Card>
                        <Card className="bg-gray-50">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm">Per Night</CardTitle>
                            <CardDescription className="text-xs">Average per night</CardDescription>
                          </CardHeader>
                          <CardContent className="pt-0">
                            {calcRange?.from && calcRange?.to ? (
                              <div className="text-2xl font-bold text-blue-700">
                                {(() => {
                                  const total = calcRecommendations.reduce((sum, r) => sum + (r.recommended_arr || 0), 0);
                                  const days = Math.ceil((calcRange.to.getTime() - calcRange.from.getTime()) / (1000 * 60 * 60 * 24)) + 1;
                                  return formatCurrency(total / days);
                                })()}
                              </div>
                            ) : (
                              <div className="text-sm text-gray-500">Select a date range.</div>
                            )}
                          </CardContent>
                        </Card>

                        <Card className="bg-gray-50">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm">Total Last Year</CardTitle>
                            <CardDescription className="text-xs">Same dates previous year</CardDescription>
                          </CardHeader>
                          <CardContent className="pt-0">
                            {calcRange?.from && calcRange?.to ? (
                              <div className="text-2xl font-bold text-emerald-700">
                                {formatCurrency(calcRecommendationsLastYear.reduce((sum, r) => sum + (r.recommended_arr || 0), 0))}
                              </div>
                            ) : (
                              <div className="text-sm text-gray-500">Select a date range.</div>
                            )}
                          </CardContent>
                        </Card>
                        <Card className="bg-gray-50">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm">Per Night Last Year</CardTitle>
                            <CardDescription className="text-xs">Average per night</CardDescription>
                          </CardHeader>
                          <CardContent className="pt-0">
                            {calcRange?.from && calcRange?.to ? (
                              <div className="text-2xl font-bold text-indigo-700">
                                {(() => {
                                  const total = calcRecommendationsLastYear.reduce((sum, r) => sum + (r.recommended_arr || 0), 0);
                                  const days = Math.ceil((calcRange.to.getTime() - calcRange.from.getTime()) / (1000 * 60 * 60 * 24)) + 1;
                                  return formatCurrency(total / days);
                                })()}
                              </div>
                            ) : (
                              <div className="text-sm text-gray-500">Select a date range.</div>
                            )}
                          </CardContent>
                        </Card>
                      </div>

                      <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-2">
                        <Card className="bg-gray-50">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm">Date Flags Summary</CardTitle>
                            <CardDescription className="text-xs">Holiday/Event/Weekend/Fasting</CardDescription>
                          </CardHeader>
                          <CardContent className="pt-0">
                            <ul className="text-sm space-y-1">
                              {(() => {
                                if (!calcRange?.from || !calcRange?.to) return <li className="text-gray-500">Select a date range.</li>;
                                const start = format(calcRange.from, 'yyyy-MM-dd');
                                const end = format(calcRange.to, 'yyyy-MM-dd');
                                const dates: string[] = [];
                                let cur = new Date(calcRange.from);
                                while (cur <= (calcRange.to as Date)) {
                                  dates.push(format(cur, 'yyyy-MM-dd'));
                                  cur.setDate(cur.getDate() + 1);
                                }
                                const flags: Record<string, string[]> = {};
                                for (const d of dates) {
                                  const day = calendarData[d] || [];
                                  if (day.length === 0) continue;
                                  const r = day[0];
                                  const labels: string[] = [];
                                  if (r.is_holiday) labels.push(r.holiday_details?.name ? `Holiday: ${r.holiday_details.name}` : 'Holiday');
                                  if (r.is_school_holiday) labels.push('School Holiday');
                                  if (r.is_event) labels.push(r.holiday_details?.name ? `Event: ${r.holiday_details.name}` : 'Event');
                                  if ((r as any).is_fasting) labels.push('Fasting');
                                  if (r.is_weekend) labels.push('Weekend');
                                  if (labels.length) flags[d] = labels;
                                }
                                const items = Object.entries(flags);
                                if (items.length === 0) return <li className="text-gray-500">No flags in range.</li>;
                                return items.map(([d, arr]) => (
                                  <li key={d} className="flex justify-between">
                                    <span className="text-gray-600">{d}</span>
                                    <span className="font-mono">{arr.join(', ')}</span>
                                  </li>
                                ));
                              })()}
                            </ul>
                          </CardContent>
                        </Card>
                        
                        <Card className="bg-gray-50">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm">Date Flags Summary (Last Year)</CardTitle>
                            <CardDescription className="text-xs">Same dates previous year</CardDescription>
                          </CardHeader>
                          <CardContent className="pt-0">
                            <ul className="text-sm space-y-1">
                              {(() => {
                                if (!calcRange?.from || !calcRange?.to) return <li className="text-gray-500">Select a date range.</li>;
                                const dates: string[] = [];
                                let cur = new Date(calcRange.from);
                                while (cur <= (calcRange.to as Date)) {
                                  const ly = new Date(cur);
                                  ly.setFullYear(ly.getFullYear() - 1);
                                  dates.push(format(ly, 'yyyy-MM-dd'));
                                  cur.setDate(cur.getDate() + 1);
                                }
                                const flags: Record<string, string[]> = {};
                                for (const d of dates) {
                                  const day = calendarData[d] || [];
                                  if (day.length === 0) continue;
                                  const r = day[0];
                                  const labels: string[] = [];
                                  if (r.is_holiday) labels.push(r.holiday_details?.name ? `Holiday: ${r.holiday_details.name}` : 'Holiday');
                                  if (r.is_school_holiday) labels.push('School Holiday');
                                  if (r.is_event) labels.push(r.holiday_details?.name ? `Event: ${r.holiday_details.name}` : 'Event');
                                  if ((r as any).is_fasting) labels.push('Fasting');
                                  if (r.is_weekend) labels.push('Weekend');
                                  if (labels.length) flags[d] = labels;
                                }
                                const items = Object.entries(flags);
                                if (items.length === 0) return <li className="text-gray-500">No flags in range.</li>;
                                return items.map(([d, arr]) => (
                                  <li key={d} className="flex justify-between">
                                    <span className="text-gray-600">{d}</span>
                                    <span className="font-mono">{arr.join(', ')}</span>
                                  </li>
                                ));
                              })()}
                            </ul>
                          </CardContent>
                        </Card>
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              </div>
          </CardContent>
        </Card>

        {/* Calendar */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calendar className="h-5 w-5" />
              Calendar ({currentDate.getFullYear()})
            </CardTitle>
            <CardDescription>
              Calendar for the current year
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
                <span className="ml-2 text-gray-600">Loading calendar data...</span>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <div className="min-w-[768px] p-4">
                  {/* Day headers */}
                  <div className="grid grid-cols-7 gap-2 mb-3">
                    {dayNames.map(day => (
                      <div key={day} className="p-3 text-center font-semibold text-gray-700 text-sm bg-gray-50 rounded-lg">
                        <span className="hidden sm:inline">{day}</span>
                        <span className="sm:hidden">{day.slice(0, 1)}</span>
                      </div>
                    ))}
                  </div>
                  
                  {/* Calendar grid */}
                  <div className="grid grid-cols-7 gap-2">
                    {calendarDays.map(day => {
                      const dateStr = format(day, 'yyyy-MM-dd');
                      const dayData = calendarData[dateStr] || [];
                      const isCurrentMonth = isSameMonth(day, currentDate);
                      const isToday = isSameDay(day, new Date());
                      const isWeekend = day.getDay() === 0 || day.getDay() === 6;
                      const isHoliday = dayData.some(d => d.is_holiday);
                      const isEvent = dayData.some(d => d.is_event);
                      const isSchoolHoliday = dayData.some(d => d.is_school_holiday);
                      const isBridge = dayData.some(d => d.is_bridge);
                      const holidayDuration = dayData[0]?.holiday_duration || 0;
                      const daysOfHoliday = dayData[0]?.days_of_holiday || 0;
                      const distanceToHoliday = dayData[0]?.distance_to_holiday || 0;
                      
                      // Debug logging for first few days
                      if (day.getDate() <= 3 && isCurrentMonth) {
                        console.log(`Day ${day.getDate()}: dateStr=${dateStr}, dayData.length=${dayData.length}`);
                        if (dayData.length > 0) {
                          console.log(`Day ${day.getDate()} data:`, dayData[0]);
                        }
                      }
                      
                      // Filter data by room type and arrangement
                      let filteredData = dayData;
                      
                      if (roomTypeFilter.length > 0) {
                        filteredData = filteredData.filter(d => roomTypeFilter.includes(d.room_type));
                      }
                      
                      if (arrangementFilter.length > 0) {
                        filteredData = filteredData.filter(d => arrangementFilter.includes(d.arrangement || ''));
                      }
                      
                      // Compute day-level occupancy once (from first rec)
                      const dayOcc = dayData.length > 0 ? dayData[0].recommended_occupancy : undefined;
                      
                      return (
                        <CalendarDayCard
                          key={dateStr}
                          date={day}
                          dayData={filteredData}
                          isCurrentMonth={isCurrentMonth}
                          isToday={isToday}
                          isWeekend={isWeekend}
                          isHoliday={isHoliday}
                          isEvent={isEvent}
                          isSchoolHoliday={isSchoolHoliday}
                          isBridge={isBridge}
                          holidayDuration={holidayDuration}
                          daysOfHoliday={daysOfHoliday}
                          distanceToHoliday={distanceToHoliday}
                          dayOccupancy={dayOcc}
                          viewMode={viewMode}
                          onClick={() => handleDayClick(day)}
                        />
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Last Year Calendar */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calendar className="h-4 w-4" />
              Last Year Calendar ({currentDate.getFullYear() - 1})
            </CardTitle>
            <CardDescription>
              Same period from the previous year for comparison
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-2">Loading last year data...</span>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <div className="min-w-[768px] p-4">
                  {/* Day headers */}
                  <div className="grid grid-cols-7 gap-2 mb-3">
                    {dayNames.map(day => (
                      <div key={day} className="p-3 text-center font-semibold text-gray-700 text-sm bg-gray-50 rounded-lg">
                        <span className="hidden sm:inline">{day}</span>
                        <span className="sm:hidden">{day.slice(0, 1)}</span>
                      </div>
                    ))}
                  </div>
                  
                  {/* Calendar grid */}
                  <div className="grid grid-cols-7 gap-2">
                    {calendarDaysLastYear.map(day => {
                      const dateStr = format(day, 'yyyy-MM-dd');
                      const dayData = calendarDataLastYear[dateStr] || [];
                      const isCurrentMonth = isSameMonth(day, new Date(currentDate.getFullYear() - 1, currentDate.getMonth()));
                      const isToday = isSameDay(day, new Date());
                      const isWeekend = day.getDay() === 0 || day.getDay() === 6;
                      const isHoliday = dayData.some(d => d.is_holiday);
                      const isEvent = dayData.some(d => d.is_event);
                      const isSchoolHoliday = dayData.some(d => d.is_school_holiday);
                      const isBridge = dayData.some(d => d.is_bridge);
                      const holidayDuration = dayData[0]?.holiday_duration || 0;
                      const daysOfHoliday = dayData[0]?.days_of_holiday || 0;
                      const distanceToHoliday = dayData[0]?.distance_to_holiday || 0;
                      
                      // Filter data by room type and arrangement
                      let filteredData = dayData;
                      
                      if (roomTypeFilter.length > 0) {
                        filteredData = filteredData.filter(d => roomTypeFilter.includes(d.room_type));
                      }
                      
                      if (arrangementFilter.length > 0) {
                        filteredData = filteredData.filter(d => arrangementFilter.includes(d.arrangement || ''));
                      }
                      
                      // Compute day-level occupancy once (from first rec)
                      const dayOcc = dayData.length > 0 ? dayData[0].recommended_occupancy : undefined;
                      
                      return (
                        <CalendarDayCard
                          key={dateStr}
                          date={day}
                          dayData={filteredData}
                          isCurrentMonth={isCurrentMonth}
                          isToday={isToday}
                          isWeekend={isWeekend}
                          isHoliday={isHoliday}
                          isEvent={isEvent}
                          isSchoolHoliday={isSchoolHoliday}
                          isBridge={isBridge}
                          holidayDuration={holidayDuration}
                          daysOfHoliday={daysOfHoliday}
                          distanceToHoliday={distanceToHoliday}
                          dayOccupancy={dayOcc}
                          viewMode={viewMode}
                          onClick={() => handleDayClick(day)}
                        />
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Legend */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="space-y-3">
                <div>
                  <h4 className="font-semibold text-sm mb-2">Day Types</h4>
                  <div className="flex flex-wrap gap-4 text-xs">
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 bg-red-50 border border-red-300 rounded"></div>
                      <span>Local Event</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 bg-teal-50 border border-teal-300 rounded"></div>
                      <span>Fasting</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 bg-yellow-50 border border-yellow-200 rounded"></div>
                      <span>National Holiday</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 bg-purple-50 border border-purple-200 rounded"></div>
                      <span>School Holiday</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 bg-orange-50 border border-orange-300 rounded"></div>
                      <span>Bridge Day</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 bg-gray-50 border border-gray-200 rounded"></div>
                      <span>Weekend</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 bg-blue-50 border-2 border-blue-500 rounded"></div>
                      <span>Today</span>
                    </div>
                  </div>
                </div>
                <div>

                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Day Details Modal */}
        <Dialog open={!!selectedDay} onOpenChange={() => setSelectedDay(null)}>
          <DialogContent className="max-w-5xl max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                {selectedDay && format(new Date(selectedDay.date), 'EEEE, MMMM dd, yyyy')}
                {selectedDay?.isHoliday && (
                  <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
                    Holiday
                  </Badge>
                )}
                {selectedDay?.recommendations && selectedDay.recommendations.length > 0 && (
                  <Badge variant="outline" className="bg-indigo-50 text-indigo-700 border-indigo-200">
                    Occ: {formatPercentage(selectedDay.recommendations[0].recommended_occupancy)}
                  </Badge>
                )}
                {selectedDay && (
                  new Date(selectedDay.date) <= new Date()
                    ? <Badge className="bg-blue-100 text-blue-800 border-blue-200">📊 Historical</Badge>
                    : <Badge className="bg-green-100 text-green-800 border-green-200">🔮 Forecast</Badge>
                )}
              </DialogTitle>
            </DialogHeader>
            
            {selectedDay && (
              <div className="space-y-4">
                {/* Holiday/Event Info */}
                {selectedDay.recommendations.length > 0 && selectedDay.recommendations[0].holiday_details && (
                  <Card className="bg-yellow-50 border-yellow-200">
                    <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                        <Info className="h-5 w-5 text-yellow-600" />
                        <div>
                          <h4 className="font-semibold text-yellow-800">
                            {selectedDay.recommendations[0].holiday_details.name}
                          </h4>
                          <p className="text-sm text-yellow-700">
                            {selectedDay.recommendations[0].holiday_details.kind} Holiday
                          </p>
                    </div>
                  </div>
                    </CardContent>
                  </Card>
                )}

                {/* Day-level drivers (collapsible) */}
                {selectedDay.recommendations.length > 0 && (
                  <Card className="bg-gray-50">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">Day Drivers</CardTitle>
                      <CardDescription className="text-xs">Shared factors for this date</CardDescription>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <Accordion type="single" collapsible className="w-full">
                        <AccordionItem value="drivers">
                          <AccordionTrigger>Show details</AccordionTrigger>
                          <AccordionContent>
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                              <div className="p-2 bg-white rounded border">
                                <span className="block text-gray-600">Holiday</span>
                                <span className="font-mono font-semibold">{selectedDay.recommendations[0].is_holiday ? 'Yes' : 'No'}</span>
                              </div>
                              <div className="p-2 bg-white rounded border">
                                <span className="block text-gray-600">Weekend</span>
                                <span className="font-mono font-semibold">{selectedDay.recommendations[0].is_weekend ? 'Yes' : 'No'}</span>
                              </div>
                              <div className="p-2 bg-white rounded border">
                                <span className="block text-gray-600">School Holiday</span>
                                <span className="font-mono font-semibold">{selectedDay.recommendations[0].is_school_holiday ? 'Yes' : 'No'}</span>
                              </div>
                              <div className="p-2 bg-white rounded border">
                                <span className="block text-gray-600">Event</span>
                                <span className="font-mono font-semibold">{selectedDay.recommendations[0].is_event ? 'Yes' : 'No'}</span>
                              </div>
                              <div className="p-2 bg-white rounded border">
                                <span className="block text-gray-600">Bridge Day</span>
                                <span className="font-mono font-semibold">{selectedDay.recommendations[0].is_bridge ? 'Yes' : 'No'}</span>
                              </div>
                              <div className="p-2 bg-white rounded border">
                                <span className="block text-gray-600">Block Length (days)</span>
                                <span className="font-mono font-semibold">{selectedDay.recommendations[0].holiday_duration ?? 0}</span>
                              </div>
                              <div className="p-2 bg-white rounded border">
                                <span className="block text-gray-600">Day in Block</span>
                                <span className="font-mono font-semibold">{selectedDay.recommendations[0].days_of_holiday ?? 0}</span>
                              </div>
                              <div className="p-2 bg-white rounded border">
                                <span className="block text-gray-600">Distance to Holiday</span>
                                <span className="font-mono font-semibold">{selectedDay.recommendations[0].distance_to_holiday ?? 0}</span>
                              </div>
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                      </Accordion>
                    </CardContent>
                  </Card>
                )}


                {/* Recommendations */}
                {selectedDay.recommendations.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Calendar className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                    <p>No recommendations available for this date and filters.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Array.from(new Set(selectedDay.recommendations.map(r => r.room_type))).map(roomType => {
                      const roomRecommendations = selectedDay.recommendations.filter(r => r.room_type === roomType);
                      const arrangementsSet = Array.from(new Set(roomRecommendations
                        .map(r => r.arrangement)
                        .filter((arr): arr is string => Boolean(arr))
                      ));
                      const arrangements = arrangementsSet;
                      const hasMultipleArrangements = arrangements.length > 1;
                      
                      // Get current arrangement based on switch state
                      const globalPref = roomTypeArrangements['__GLOBAL__'];
                      const currentArrangement = hasMultipleArrangements 
                        ? (globalPref ? (globalPref.RB ? 'RB' : 'RO') : (roomTypeArrangements[roomType]?.RB ? 'RB' : 'RO'))
                        : (arrangements[0] || null);
                      
                      const currentRecommendation = roomRecommendations.find(r => r.arrangement === currentArrangement) || roomRecommendations[0];
                      
                      return (
                    <RecommendationCard 
                          key={roomType} 
                          recommendation={currentRecommendation}
                          roomType={roomType}
                          arrangements={arrangements}
                          currentArrangement={currentArrangement}
                          hasMultipleArrangements={hasMultipleArrangements}
                          roomTypeArrangements={roomTypeArrangements}
                          setRoomTypeArrangements={setRoomTypeArrangements}
                        />
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}

interface CalendarDayCardProps {
  date: Date;
  dayData: Recommendation[];
  isCurrentMonth: boolean;
  isToday: boolean;
  isWeekend: boolean;
  isHoliday: boolean;
  isEvent: boolean;
  isSchoolHoliday: boolean;
  isBridge?: boolean;
  holidayDuration?: number;
  daysOfHoliday?: number;
  distanceToHoliday?: number;
  dayOccupancy?: number;
  viewMode: ViewMode;
  onClick: () => void;
}

function CalendarDayCard({ date, dayData, isCurrentMonth, isToday, isWeekend, isHoliday, isEvent, isSchoolHoliday, isBridge, holidayDuration, daysOfHoliday, distanceToHoliday, dayOccupancy, viewMode, onClick }: CalendarDayCardProps) {
  const height = viewMode === 'week' ? 'min-h-[120px]' : 'min-h-[100px]';
  
  let cellClasses = `${height} p-3 border-2 relative cursor-pointer transition-all duration-200 rounded-lg hover:shadow-md`;
  
  if (isEvent) {
    cellClasses += ' bg-red-50 border-red-300 hover:bg-red-100';
  } else if (isHoliday) {
    cellClasses += ' bg-yellow-50 border-yellow-200 hover:bg-yellow-100';
  } else if (dayData.length > 0 && dayData[0].is_fasting) {
    cellClasses += ' bg-teal-50 border-teal-300 hover:bg-teal-100';
  } else if (isSchoolHoliday) {
    cellClasses += ' bg-purple-50 border-purple-300 hover:bg-purple-100';
  } else if (isBridge) {
    cellClasses += ' bg-orange-50 border-orange-300 hover:bg-orange-100';
  } else if (isWeekend) {
    cellClasses += ' bg-gray-50 border-gray-200 hover:bg-gray-100';
  } else {
    cellClasses += ' bg-white border-gray-200 hover:bg-blue-50 hover:border-blue-300';
  }
  
  if (!isCurrentMonth) {
    cellClasses += ' opacity-40';
  }
  
  if (isToday) {
    cellClasses += ' ring-2 ring-blue-500 shadow-lg border-blue-300';
  }

  return (
    <div className={cellClasses} onClick={onClick}>
      <div className={`font-semibold text-sm mb-2 flex justify-between items-start ${isToday ? 'text-blue-600' : 'text-gray-700'}`}>
        <span>{date.getDate()}</span>
        {typeof dayOccupancy === 'number' && (
          (() => {
            const p = dayOccupancy;
            let cls = 'bg-gray-100 text-gray-700 border-gray-200';
            if (p <= 0.2) cls = 'bg-red-100 text-red-800 border-red-200';
            else if (p <= 0.4) cls = 'bg-orange-100 text-orange-800 border-orange-200';
            else if (p <= 0.6) cls = 'bg-amber-100 text-amber-800 border-amber-200';
            else if (p <= 0.8) cls = 'bg-lime-100 text-lime-800 border-lime-200';
            else cls = 'bg-green-100 text-green-800 border-green-200';
            return (
              <span className={`text-[10px] px-1.5 py-0.5 rounded border ${cls}`}>
                {formatPercentage(dayOccupancy)}
              </span>
            );
          })()
        )}
        {isHoliday && dayData.length > 0 && dayData[0].holiday_details && (
          <div 
            className="w-2 h-2 bg-yellow-500 rounded-full flex-shrink-0"
            title={dayData[0].holiday_details.name}
          />
        )}
      </div>
      
      <div className="space-y-1">
        {dayData.length === 0 && (
          <div className="text-xs text-gray-400 text-center py-1">
            No data
          </div>
        )}
        {dayData.slice(0, viewMode === 'week' ? 4 : 3).map((rec, idx) => {
          const roomTypeShort = rec.room_type.split(' ')[0];
          const priceShort = formatCurrencyShort(rec.recommended_arr);
          
          return (
            <div
              key={idx}
              className={`text-xs px-2 py-1 rounded border border-gray-300 bg-white text-gray-700 block truncate`}
              title={`${rec.room_type}: ${formatCurrency(rec.recommended_arr)}`}
            >
              <div className="flex justify-between items-center">
                <span className="font-medium">{roomTypeShort}</span>
                <span>{priceShort}</span>
              </div>
            </div>
          );
        })}
        {dayData.length > (viewMode === 'week' ? 4 : 3) && (
          <div className="text-xs text-gray-500 text-center py-1">
            +{dayData.length - (viewMode === 'week' ? 4 : 3)} more
          </div>
        )}
      </div>
    </div>
  );
}

interface RecommendationCardProps {
  recommendation: Recommendation;
  roomType: string;
  arrangements: string[];
  currentArrangement: string | null;
  hasMultipleArrangements: boolean;
  roomTypeArrangements: Record<string, { RB: boolean; RO: boolean }>;
  setRoomTypeArrangements: React.Dispatch<React.SetStateAction<Record<string, { RB: boolean; RO: boolean }>>>;
}

function RecommendationCard({ recommendation, roomType, arrangements, currentArrangement, hasMultipleArrangements, roomTypeArrangements, setRoomTypeArrangements }: RecommendationCardProps) {
  const isHistorical = new Date(recommendation.date) <= new Date();
  
  return (
    <Card className="border-l-4 border-l-blue-500">
      <CardContent className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Info */}
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="border-gray-300 text-gray-700">
                {recommendation.room_type}
              </Badge>
                {recommendation.arrangement && (
                  <Badge variant="outline" className="border-gray-300 text-gray-700">
                    {recommendation.arrangement}
                </Badge>
                )}
              </div>
              
              {/* Arrangement Switch */}
              {hasMultipleArrangements && (
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium">RO</span>
                  <Switch
                    checked={roomTypeArrangements[roomType]?.RB ?? true}
                    onCheckedChange={(checked: boolean) => {
                      setRoomTypeArrangements((prev: Record<string, { RB: boolean; RO: boolean }>) => ({
                        ...prev,
                        [roomType]: {
                          ...prev[roomType],
                          RB: checked,
                          RO: !checked
                        }
                      }));
                    }}
                  />
                  <span className="text-sm font-medium">RB</span>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-green-50 p-4 rounded-lg">
                <p className="text-sm text-green-600 font-medium">ARR</p>
                <p className="text-2xl font-bold text-green-700">
                  {formatCurrency(recommendation.recommended_arr)}
                </p>
              </div>
            </div>

            {/* Removed day-level drivers here (kept at modal-level above) */}
            </div>

          {/* Removed legacy considerations panel */}
        </div>
      </CardContent>
    </Card>
  );
}
