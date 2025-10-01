"use client";

import * as React from "react";
import { format } from "date-fns";
import { Calendar as CalendarIcon } from "lucide-react";
import { DateRange } from "react-day-picker";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

interface DateRangePickerProps {
  dateRange: DateRange | undefined;
  onDateRangeChange: (dateRange: DateRange | undefined) => void;
  className?: string;
  placeholder?: string;
}

export function DateRangePicker({ dateRange, onDateRangeChange, className, placeholder = "Pick a date range" }: DateRangePickerProps) {
  const [open, setOpen] = React.useState(false);
  const [currentMonth, setCurrentMonth] = React.useState<Date>(dateRange?.from || new Date());

  const currentYear = currentMonth.getFullYear();
  const currentMonthIndex = currentMonth.getMonth();

  const handleSelect = (range: DateRange | undefined) => {
    if (range?.from && !range.to) {
      onDateRangeChange({ from: range.from, to: range.from });
    } else {
      onDateRangeChange(range);
    }
  };

  return (
    <div className={cn("grid gap-2", className)}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button id="date" variant={"outline"} className={cn("w-full justify-start text-left font-normal", !dateRange && "text-muted-foreground")}>
            <CalendarIcon className="mr-2 h-4 w-4" />
            {dateRange?.from ? (
              dateRange.to ? (
                <>
                  {format(dateRange.from, "LLL dd, y")} - {format(dateRange.to, "LLL dd, y")}
                </>
              ) : (
                format(dateRange.from, "LLL dd, y")
              )
            ) : (
              <span>{placeholder}</span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            initialFocus
            mode="range"
            selected={dateRange}
            onSelect={handleSelect}
            numberOfMonths={1}
            month={currentMonth}
            onMonthChange={setCurrentMonth}
            // Menonaktifkan header bawaan kalender
            showOutsideDays={false}
            captionLayout="dropdown"
            className="[&_[data-description]]:hidden"
            fromYear={2024}
            toYear={2026}
          />

          <div className="p-3 border-t">
            <Button onClick={() => setOpen(false)} className="w-full" disabled={!dateRange?.from}>
              Done
            </Button>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}