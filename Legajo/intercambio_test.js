import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: Number(__ENV.VUS || 100),
  duration: __ENV.DURATION || '30s',
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<1200'],
    checks: ['rate>0.95'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000';
const ENDPOINT = '/api/intercambios';
const SESSIONID = __ENV.SESSIONID || '';

export default function () {
  const params = {
    headers: {
      Accept: 'application/json',
      ...(SESSIONID ? { Cookie: `sessionid=${SESSIONID}` } : {}),
    },
  };

  const res = http.get(`${BASE_URL}${ENDPOINT}`, params);

  check(res, {
    'intercambios responde estado esperado': (response) => (
      SESSIONID ? response.status === 200 : response.status === 401
    ),
  });

  sleep(1);
}
