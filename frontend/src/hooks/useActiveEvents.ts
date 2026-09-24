import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import type { ActiveEventsResponse } from '../types';

export function useActiveEvents(autoRefreshIntervalMs: number = 0) {
  const [data, setData] = useState<ActiveEventsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEvents = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getActiveEvents();
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch active events');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEvents();

    if (autoRefreshIntervalMs > 0) {
      const timer = setInterval(fetchEvents, autoRefreshIntervalMs);
      return () => clearInterval(timer);
    }
  }, [fetchEvents, autoRefreshIntervalMs]);

  return { data, loading, error, refresh: fetchEvents };
}
