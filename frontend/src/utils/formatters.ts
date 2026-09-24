/**
 * Utility functions for FieryVision AI
 */


export function getClassificationColor(classification?: string | null): string {
  if (!classification) return 'white';
  const val = classification.toLowerCase();
  if (val.includes('industrial fire')) return 'red';
  if (val.includes('persistent industrial')) return 'orange';
  if (val.includes('agricultural')) return 'green';
  if (val.includes('natural') || val.includes('forest')) return 'blue';
  return 'white';
}

export function getPriorityColor(priority?: string | null): {
  bg: string;
  text: string;
  border: string;
} {
  const p = (priority || '').toLowerCase();
  if (p === 'critical') {
    return {
      bg: 'bg-red-500/20',
      text: 'text-red-400',
      border: 'border-red-500/40',
    };
  }
  if (p === 'high') {
    return {
      bg: 'bg-orange-500/20',
      text: 'text-orange-400',
      border: 'border-orange-500/40',
    };
  }
  if (p === 'moderate' || p === 'medium') {
    return {
      bg: 'bg-amber-500/20',
      text: 'text-amber-400',
      border: 'border-amber-500/40',
    };
  }
  if (p === 'low') {
    return {
      bg: 'bg-emerald-500/20',
      text: 'text-emerald-400',
      border: 'border-emerald-500/40',
    };
  }
  return {
    bg: 'bg-slate-500/20',
    text: 'text-slate-400',
    border: 'border-slate-500/40',
  };
}

export function formatCoordinate(lat: number, lon: number): string {
  return `${lat.toFixed(5)}°N, ${lon.toFixed(5)}°E`;
}

export function formatDistance(distanceM?: number | null): string {
  if (distanceM === undefined || distanceM === null) return 'N/A';
  if (distanceM < 1000) return `${Math.round(distanceM)} m`;
  return `${(distanceM / 1000).toFixed(2)} km`;
}

export function formatDateTime(date?: string | null, time?: string | null): string {
  if (!date) return 'Unknown';
  if (!time) return date;
  // If time is e.g. 1345, format as 13:45
  const formattedTime = time.length === 4 ? `${time.slice(0, 2)}:${time.slice(2)} UTC` : `${time} UTC`;
  return `${date} ${formattedTime}`;
}

export function escapeHtml(value: string | number | undefined | null): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
