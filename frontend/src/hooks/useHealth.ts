import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import type { HealthResponse } from '../types';

export function useHealth(pollIntervalMs: number = 30000) {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [online, setOnline] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  const checkHealth = useCallback(async () => {
    try {
      const res = await api.getHealth();
      setData(res);
      setOnline(res.status === 'ok');
    } catch {
      setOnline(false);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    if (pollIntervalMs > 0) {
      const timer = setInterval(checkHealth, pollIntervalMs);
      return () => clearInterval(timer);
    }
  }, [checkHealth, pollIntervalMs]);

  return { data, online, loading, refresh: checkHealth };
}
