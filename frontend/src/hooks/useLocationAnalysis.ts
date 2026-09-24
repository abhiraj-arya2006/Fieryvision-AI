import { useState, useCallback } from 'react';
import api from '../services/api';
import type { LocationAnalysisResponse } from '../types';

export function useLocationAnalysis() {
  const [data, setData] = useState<LocationAnalysisResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const analyse = useCallback(async (latitude: number, longitude: number) => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.analyseLocation(latitude, longitude);
      setData(res);
      return res;
    } catch (err: any) {
      const msg = err?.message || 'Location analysis failed';
      setError(msg);
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

  return { data, loading, error, analyse, reset };
}
