/**
 * Rung Stress Test Suite
 *
 * Tests system behavior under extreme load conditions.
 * Identifies breaking points and validates graceful degradation.
 *
 * Run: k6 run scripts/load_tests/stress_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';
import { randomString, randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// Custom metrics
const errorRate = new Rate('errors');
const requestLatency = new Trend('request_latency', true);
const breakingPointVUs = new Counter('breaking_point_vus');

// Configuration
const BASE_URL = __ENV.API_URL || 'https://api.rung.health';

// Stress test options - ramp to breaking point
export const options = {
    stages: [
        { duration: '30s', target: 50 },    // Warm up
        { duration: '1m', target: 100 },    // Normal load
        { duration: '1m', target: 200 },    // High load
        { duration: '1m', target: 300 },    // Very high load
        { duration: '1m', target: 400 },    // Stress load
        { duration: '1m', target: 500 },    // Breaking point test
        { duration: '2m', target: 500 },    // Sustained stress
        { duration: '1m', target: 0 },      // Recovery
    ],
    thresholds: {
        // Under stress, allow higher error rates but track them
        'errors': ['rate<0.10'],  // 10% error tolerance under stress

        // Latency thresholds for stress testing
        'request_latency': ['p(95)<10000'],  // 10s P95 under stress
        'http_req_duration': ['p(99)<30000'],  // 30s P99 absolute max
    },
};

// Rapid-fire health checks
function stressHealthCheck() {
    const startTime = Date.now();
    const response = http.get(`${BASE_URL}/health`, {
        timeout: '30s',
        tags: { name: 'stress_health' },
    });
    requestLatency.add(Date.now() - startTime);

    const success = response.status === 200;
    errorRate.add(success ? 0 : 1);

    if (!success && response.status >= 500) {
        breakingPointVUs.add(__VU);
    }

    return success;
}

// Concurrent API calls simulation
function stressApiCalls(token) {
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    };

    // Fire multiple requests in quick succession
    const requests = [
        ['GET', `${BASE_URL}/api/v1/clients`, null],
        ['GET', `${BASE_URL}/api/v1/sessions`, null],
        ['POST', `${BASE_URL}/api/v1/voice-memos`, JSON.stringify({
            client_id: 'stress_test',
            memo_content: randomString(500),
        })],
    ];

    let errors = 0;
    const startTime = Date.now();

    for (const [method, url, body] of requests) {
        let response;
        if (method === 'GET') {
            response = http.get(url, { headers, tags: { name: 'stress_api' } });
        } else {
            response = http.post(url, body, { headers, tags: { name: 'stress_api' } });
        }

        if (response.status >= 500) {
            errors++;
            breakingPointVUs.add(__VU);
        }
    }

    requestLatency.add(Date.now() - startTime);
    errorRate.add(errors > 0 ? 1 : 0);
}

// Large payload test
function stressLargePayload(token) {
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    };

    // Large voice memo (10KB of content)
    const largeContent = randomString(10000);
    const payload = JSON.stringify({
        client_id: 'stress_test',
        memo_content: largeContent,
        duration_seconds: 600,
    });

    const startTime = Date.now();
    const response = http.post(
        `${BASE_URL}/api/v1/voice-memos`,
        payload,
        { headers, timeout: '60s', tags: { name: 'stress_large_payload' } }
    );
    requestLatency.add(Date.now() - startTime);

    const success = response.status < 500;
    errorRate.add(success ? 0 : 1);

    if (!success) {
        breakingPointVUs.add(__VU);
    }
}

// Connection burst test
function stressConnectionBurst() {
    const startTime = Date.now();

    // Rapid connection attempts
    const responses = http.batch([
        ['GET', `${BASE_URL}/health`],
        ['GET', `${BASE_URL}/health`],
        ['GET', `${BASE_URL}/health`],
        ['GET', `${BASE_URL}/health`],
        ['GET', `${BASE_URL}/health`],
    ]);

    requestLatency.add(Date.now() - startTime);

    let errors = 0;
    for (const response of responses) {
        if (response.status >= 500) {
            errors++;
        }
    }

    errorRate.add(errors > 0 ? 1 : 0);
    if (errors > 0) {
        breakingPointVUs.add(__VU);
    }
}

// Main stress test function
export default function() {
    const testChoice = Math.random();

    if (testChoice < 0.40) {
        // Health check stress (40%)
        stressHealthCheck();
    } else if (testChoice < 0.70) {
        // API stress (30%)
        const token = 'stress_test_token';
        stressApiCalls(token);
    } else if (testChoice < 0.85) {
        // Large payload stress (15%)
        const token = 'stress_test_token';
        stressLargePayload(token);
    } else {
        // Connection burst (15%)
        stressConnectionBurst();
    }

    // Minimal think time under stress
    sleep(randomIntBetween(0.1, 0.5));
}

// Setup function
export function setup() {
    console.log(`Starting stress test against ${BASE_URL}`);
    console.log('Ramping to 500 concurrent users to find breaking point');

    return { startTime: Date.now() };
}

// Teardown function
export function teardown(data) {
    const duration = (Date.now() - data.startTime) / 1000;
    console.log(`Stress test completed in ${duration.toFixed(2)} seconds`);
}

// Summary handler
export function handleSummary(data) {
    const metrics = data.metrics;

    let summary = '\n=== Rung Stress Test Results ===\n\n';
    summary += 'Stress Test Metrics:\n';
    summary += `  Total Requests: ${metrics.http_reqs?.values?.count || 0}\n`;
    summary += `  Request Duration P95: ${(metrics.http_req_duration?.values?.['p(95)'] || 0).toFixed(2)}ms\n`;
    summary += `  Request Duration P99: ${(metrics.http_req_duration?.values?.['p(99)'] || 0).toFixed(2)}ms\n`;
    summary += `  Error Rate: ${((metrics.errors?.values?.rate || 0) * 100).toFixed(2)}%\n`;
    summary += `  Breaking Point Events: ${metrics.breaking_point_vus?.values?.count || 0}\n`;
    summary += '\n';

    // Threshold results
    summary += 'Threshold Results:\n';
    for (const [name, threshold] of Object.entries(data.thresholds || {})) {
        const status = threshold.ok ? 'PASS' : 'FAIL';
        summary += `  ${name}: ${status}\n`;
    }

    return {
        'stdout': summary,
        'scripts/load_tests/results/stress_summary.json': JSON.stringify(data, null, 2),
    };
}
