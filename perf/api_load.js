import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  stages: [
    { duration: "30s", target: 20 },  // ramp up to 20 virtual users
    { duration: "1m", target: 20 },   // hold
    { duration: "15s", target: 0 },   // ramp down
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"],    // under 1% errors
    http_req_duration: ["p(95)<300"],  // 95% of requests under 300 ms
  },
};

export default function () {
  const top = http.get(`${BASE}/v1/rankings/top?medium=game&limit=25`);
  check(top, { "rankings 200": (r) => r.status === 200 });

  const page = Math.ceil(Math.random() * 5);
  const list = http.get(`${BASE}/v1/media?medium=movie&min_score=70&page=${page}`);
  check(list, { "list 200": (r) => r.status === 200 });

  sleep(1);
}
