export const getApiBaseUrl = (): string => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  return baseUrl.replace(/\/+$/, '');
};

export const getWsUrl = (): string => {
  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
  return wsUrl.replace(/\/+$/, '');
};
