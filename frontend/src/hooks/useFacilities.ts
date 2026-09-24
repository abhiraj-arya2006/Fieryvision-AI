import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import type { FacilitiesResponse } from '../types';

export function useFacilities() {
  const [data, setData] = useState<FacilitiesResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFacilities = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getFacilities();
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch facilities');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFacilities();
  }, [fetchFacilities]);

  return { data, loading, error, refresh: fetchFacilities };
}
