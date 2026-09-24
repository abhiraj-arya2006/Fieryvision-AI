import { useState, useCallback } from 'react';
import api from '../services/api';
import type { SatelliteContextResponse } from '../types';

export function useSatelliteContext() {
  const [data, setData] = useState<SatelliteContextResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchContext = useCallback(async (eventId: string) => {
    if (!eventId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.getSatelliteContext(eventId);
      setData(res);
      return res;
    } catch (err: any) {
      setError(err?.message || 'Failed to retrieve satellite context');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { data, loading, error, fetchContext, reset };
}
