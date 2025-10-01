import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { format, parseISO } from "date-fns"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatCurrencyShort(amount: number): string {
  if (amount >= 1000000000) {
    return `${(amount / 1000000000).toFixed(1)}B`;
  } else if (amount >= 1000000) {
    return `${(amount / 1000000).toFixed(1)}M`;
  } else if (amount >= 1000) {
    return `${(amount / 1000).toFixed(0)}K`;
  }
  return amount.toString();
}

export function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function formatDate(dateString: string): string {
  try {
    return format(parseISO(dateString), 'MMM dd, yyyy');
  } catch {
    return dateString;
  }
}

export function formatDateShort(dateString: string): string {
  try {
    return format(parseISO(dateString), 'MMM dd');
  } catch {
    return dateString;
  }
}

export function getRoomTypeColor(roomType: string): string {
  const colors: Record<string, string> = {
    'Deluxe': 'bg-blue-100 text-blue-800 border-blue-200',
    'Executive Suite': 'bg-orange-100 text-orange-800 border-orange-200',
    'Suite': 'bg-green-100 text-green-800 border-green-200',
    'Family Suite': 'bg-pink-100 text-pink-800 border-pink-200',
  };
  
  return colors[roomType] || 'bg-gray-100 text-gray-800 border-gray-200';
}

export function getConfidenceColor(confidence: string): string {
  const colors: Record<string, string> = {
    'High': 'bg-green-100 text-green-800 border-green-200',
    'Medium': 'bg-yellow-100 text-yellow-800 border-yellow-200',
    'Low': 'bg-red-100 text-red-800 border-red-200',
  };
  
  return colors[confidence] || 'bg-gray-100 text-gray-800 border-gray-200';
}

export function getConfidenceBorderColor(confidence: string): string {
  const colors: Record<string, string> = {
    'High': 'border-l-green-500',
    'Medium': 'border-l-yellow-500',
    'Low': 'border-l-red-500',
  };
  
  return colors[confidence] || 'border-l-gray-500';
}
