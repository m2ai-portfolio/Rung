# Rung Load Testing Suite

k6-based load testing for validating Rung API performance requirements.

## Requirements

- [k6](https://k6.io/docs/getting-started/installation/) installed
- Access to Rung API (staging or production)
- Test credentials (optional, for authenticated workflows)

## Installation

```bash
# Install k6 on Ubuntu/Debian
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# Or via Docker
docker pull grafana/k6
```

## Test Files

| File | Purpose | Target VUs |
|------|---------|------------|
| `load_test.js` | Standard load test | 100 |
| `stress_test.js` | Breaking point test | 500 |

## Performance Requirements

| Metric | Requirement | Measured By |
|--------|-------------|-------------|
| P95 Latency | < 5 seconds | All workflows |
| Error Rate | < 5% | All requests |
| Concurrent Users | 100 | load_test.js |

## Usage

### Basic Load Test (100 VUs)

```bash
# Using default options
k6 run scripts/load_tests/load_test.js

# With custom API URL
API_URL=https://api.staging.rung.health k6 run scripts/load_tests/load_test.js

# With authentication
TEST_USERNAME=test@example.com TEST_PASSWORD=secret k6 run scripts/load_tests/load_test.js
```

### Quick Smoke Test

```bash
k6 run --vus 5 --duration 30s scripts/load_tests/load_test.js
```

### Full Load Test

```bash
k6 run --vus 100 --duration 10m scripts/load_tests/load_test.js
```

### Stress Test (Breaking Point)

```bash
k6 run scripts/load_tests/stress_test.js
```

### Using Docker

```bash
docker run --rm -i \
  -e API_URL=https://api.rung.health \
  -v $(pwd)/scripts/load_tests:/scripts \
  grafana/k6 run /scripts/load_test.js
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_URL` | Base API URL | `https://api.rung.health` |
| `AUTH_URL` | Auth service URL | `https://auth.rung.health` |
| `TEST_USERNAME` | Test account username | Random |
| `TEST_PASSWORD` | Test account password | Random |

## Output

Results are saved to `scripts/load_tests/results/`:

- `summary.json` - Load test results
- `stress_summary.json` - Stress test results

### Sample Output

```
=== Rung Load Test Results ===

Key Performance Metrics:
  HTTP Requests: 15234
  Request Duration P95: 2345.67ms
  Error Rate: 0.12%

Workflow Latencies (P95):
  Pre-Session: 3456.78ms
  Post-Session: 2890.12ms
  Couples Merge: 4123.45ms
  Authentication: 890.23ms

Threshold Results:
  errors: PASS
  pre_session_latency: PASS
  post_session_latency: PASS
  couples_merge_latency: PASS
  http_req_duration: PASS
```

## Workflow Distribution

The load test simulates realistic traffic patterns:

| Workflow | Percentage |
|----------|------------|
| Pre-Session | 35% |
| Post-Session | 35% |
| Client Data Retrieval | 15% |
| Couples Merge | 15% |

## Thresholds

### Load Test (load_test.js)

- Error rate < 5%
- All workflow P95 < 5000ms
- HTTP request P95 < 5000ms
- HTTP request P99 < 10000ms

### Stress Test (stress_test.js)

- Error rate < 10% (higher tolerance under stress)
- Request P95 < 10000ms
- HTTP request P99 < 30000ms

## CI/CD Integration

```yaml
# GitHub Actions example
- name: Run Load Tests
  run: |
    k6 run --vus 100 --duration 5m \
      -e API_URL=${{ secrets.STAGING_API_URL }} \
      scripts/load_tests/load_test.js
```

## Troubleshooting

### High Error Rate

1. Check API logs for 5xx errors
2. Verify Lambda provisioned concurrency
3. Check RDS connection pool limits
4. Review CloudWatch metrics for bottlenecks

### High Latency

1. Check Bedrock service latency
2. Review database query performance
3. Verify VPC endpoint configuration
4. Check for cold start issues

### Connection Errors

1. Verify API Gateway limits
2. Check ALB connection limits
3. Review security group rules
4. Verify SSL/TLS configuration
