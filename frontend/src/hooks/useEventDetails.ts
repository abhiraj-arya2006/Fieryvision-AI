import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import type { CanonicalEvent } from '../types';

export function useEventDetails(eventId: string | null) {
  const [event, setEvent] = useState<CanonicalEvent | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchEvent = useCallback(async () => {
    if (!eventId) {
      setEvent(null);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const res = await api.getEvent(eventId);
      setEvent(res);
    } catch (err: any) {
      setError(err?.message || `Failed to fetch event ${eventId}`);
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    fetchEvent();
  }, [fetchEvent]);

  return { event, loading, error, refresh: fetchEvent };
}
