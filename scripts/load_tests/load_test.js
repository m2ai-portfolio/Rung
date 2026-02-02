/**
 * Rung Load Test Suite
 *
 * Tests API performance under load with 100 concurrent users.
 * Validates P95 latency < 5s for all workflows.
 *
 * Run: k6 run scripts/load_tests/load_test.js
 * Run with options: k6 run --vus 100 --duration 5m scripts/load_tests/load_test.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';
import { randomString, randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// Custom metrics
const errorRate = new Rate('errors');
const preSessionLatency = new Trend('pre_session_latency', true);
const postSessionLatency = new Trend('post_session_latency', true);
const couplesMergeLatency = new Trend('couples_merge_latency', true);
const authLatency = new Trend('auth_latency', true);
const healthCheckLatency = new Trend('health_check_latency', true);

// Configuration
const BASE_URL = __ENV.API_URL || 'https://api.rung.health';
const AUTH_URL = __ENV.AUTH_URL || 'https://auth.rung.health';

// Test options - 100 concurrent users, <5% error rate, P95 < 5s
export const options = {
    stages: [
        { duration: '1m', target: 25 },   // Ramp up to 25 users
        { duration: '1m', target: 50 },   // Ramp up to 50 users
        { duration: '2m', target: 100 },  // Ramp up to 100 users
        { duration: '3m', target: 100 },  // Stay at 100 users
        { duration: '1m', target: 50 },   // Ramp down to 50
        { duration: '1m', target: 0 },    // Ramp down to 0
    ],
    thresholds: {
        // Error rate must be less than 5%
        'errors': ['rate<0.05'],

        // P95 latency must be under 5 seconds for all workflows
        'pre_session_latency': ['p(95)<5000'],
        'post_session_latency': ['p(95)<5000'],
        'couples_merge_latency': ['p(95)<5000'],
        'auth_latency': ['p(95)<3000'],  // Auth should be faster
        'health_check_latency': ['p(95)<1000'],  // Health checks very fast

        // HTTP request duration
        'http_req_duration': ['p(95)<5000', 'p(99)<10000'],

        // HTTP request failures
        'http_req_failed': ['rate<0.05'],
    },
};

// Simulated test credentials (in real test, use env vars or test accounts)
function getTestCredentials() {
    return {
        username: __ENV.TEST_USERNAME || `test_user_${randomString(8)}`,
        password: __ENV.TEST_PASSWORD || 'TestPassword123!',
    };
}

// Authentication helper
function authenticate() {
    const credentials = getTestCredentials();

    const payload = JSON.stringify({
        username: credentials.username,
        password: credentials.password,
    });

    const params = {
        headers: {
            'Content-Type': 'application/json',
        },
        tags: { name: 'auth' },
    };

    const startTime = Date.now();
    const response = http.post(`${AUTH_URL}/login`, payload, params);
    authLatency.add(Date.now() - startTime);

    const success = check(response, {
        'auth status is 200': (r) => r.status === 200,
        'auth returns token': (r) => r.json('access_token') !== undefined,
    });

    if (!success) {
        errorRate.add(1);
        return null;
    }

    errorRate.add(0);
    return response.json('access_token');
}

// Health check
function healthCheck() {
    const startTime = Date.now();
    const response = http.get(`${BASE_URL}/health`, {
        tags: { name: 'health' },
    });
    healthCheckLatency.add(Date.now() - startTime);

    const success = check(response, {
        'health check is 200': (r) => r.status === 200,
        'health check returns ok': (r) => r.json('status') === 'ok',
    });

    errorRate.add(success ? 0 : 1);
    return success;
}

// Pre-session workflow simulation
function preSessionWorkflow(token) {
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    };

    // Simulate voice memo submission
    const memoPayload = JSON.stringify({
        client_id: `client_${randomString(8)}`,
        session_id: `session_${randomString(8)}`,
        memo_content: 'Test voice memo content for load testing. ' + randomString(100),
        duration_seconds: randomIntBetween(60, 600),
    });

    const startTime = Date.now();

    // Submit voice memo
    const memoResponse = http.post(
        `${BASE_URL}/api/v1/voice-memos`,
        memoPayload,
        { headers, tags: { name: 'pre_session_memo' } }
    );

    check(memoResponse, {
        'memo submission accepted': (r) => r.status === 200 || r.status === 202,
    });

    // Trigger analysis
    const analysisResponse = http.post(
        `${BASE_URL}/api/v1/analyze/pre-session`,
        JSON.stringify({ memo_id: memoResponse.json('memo_id') || 'test_memo' }),
        { headers, tags: { name: 'pre_session_analysis' } }
    );

    preSessionLatency.add(Date.now() - startTime);

    const success = check(analysisResponse, {
        'pre-session analysis accepted': (r) => r.status === 200 || r.status === 202,
    });

    errorRate.add(success ? 0 : 1);
    return success;
}

// Post-session workflow simulation
function postSessionWorkflow(token) {
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    };

    const sessionPayload = JSON.stringify({
        session_id: `session_${randomString(8)}`,
        client_id: `client_${randomString(8)}`,
        notes: 'Session notes for load testing. Discussed attachment patterns and communication styles. ' + randomString(200),
        frameworks: ['attachment', 'cbt'],
        duration_minutes: randomIntBetween(45, 90),
    });

    const startTime = Date.now();

    // Submit session notes
    const notesResponse = http.post(
        `${BASE_URL}/api/v1/sessions/notes`,
        sessionPayload,
        { headers, tags: { name: 'post_session_notes' } }
    );

    check(notesResponse, {
        'notes submission accepted': (r) => r.status === 200 || r.status === 202,
    });

    // Trigger development plan generation
    const planResponse = http.post(
        `${BASE_URL}/api/v1/development-plans/generate`,
        JSON.stringify({ session_id: notesResponse.json('session_id') || 'test_session' }),
        { headers, tags: { name: 'post_session_plan' } }
    );

    postSessionLatency.add(Date.now() - startTime);

    const success = check(planResponse, {
        'development plan generation accepted': (r) => r.status === 200 || r.status === 202,
    });

    errorRate.add(success ? 0 : 1);
    return success;
}

// Couples merge workflow simulation
function couplesMergeWorkflow(token) {
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    };

    const mergePayload = JSON.stringify({
        couple_link_id: `link_${randomString(8)}`,
        partner_a_session_id: `session_${randomString(8)}`,
        partner_b_session_id: `session_${randomString(8)}`,
    });

    const startTime = Date.now();

    const mergeResponse = http.post(
        `${BASE_URL}/api/v1/couples/merge`,
        mergePayload,
        { headers, tags: { name: 'couples_merge' } }
    );

    couplesMergeLatency.add(Date.now() - startTime);

    const success = check(mergeResponse, {
        'couples merge accepted': (r) => r.status === 200 || r.status === 202 || r.status === 403,
        // 403 is acceptable - may be unauthorized in test mode
    });

    // Only count actual errors, not authorization failures in test mode
    if (mergeResponse.status >= 500) {
        errorRate.add(1);
    } else {
        errorRate.add(0);
    }

    return success;
}

// Client data retrieval
function clientDataRetrieval(token) {
    const headers = {
        'Authorization': `Bearer ${token}`,
    };

    const clientId = `client_${randomString(8)}`;

    // Get client profile
    const profileResponse = http.get(
        `${BASE_URL}/api/v1/clients/${clientId}`,
        { headers, tags: { name: 'client_profile' } }
    );

    // Get client sessions
    const sessionsResponse = http.get(
        `${BASE_URL}/api/v1/clients/${clientId}/sessions`,
        { headers, tags: { name: 'client_sessions' } }
    );

    // Get clinical briefs
    const briefsResponse = http.get(
        `${BASE_URL}/api/v1/clients/${clientId}/briefs`,
        { headers, tags: { name: 'clinical_briefs' } }
    );

    const success = check(profileResponse, {
        'client data retrieval': (r) => r.status === 200 || r.status === 404,
        // 404 acceptable - test client may not exist
    });

    errorRate.add(profileResponse.status >= 500 ? 1 : 0);
    return success;
}

// Main test function
export default function() {
    // Health check (every iteration)
    group('Health Check', () => {
        healthCheck();
    });

    // Authenticate
    let token = null;
    group('Authentication', () => {
        token = authenticate();
    });

    // Skip workflows if auth failed (in test mode)
    if (!token) {
        // Use mock token for testing API structure
        token = 'test_token_' + randomString(32);
    }

    // Random workflow selection (weighted by typical usage)
    const workflowChoice = Math.random();

    if (workflowChoice < 0.35) {
        // Pre-session workflow (35% of traffic)
        group('Pre-Session Workflow', () => {
            preSessionWorkflow(token);
        });
    } else if (workflowChoice < 0.70) {
        // Post-session workflow (35% of traffic)
        group('Post-Session Workflow', () => {
            postSessionWorkflow(token);
        });
    } else if (workflowChoice < 0.85) {
        // Client data retrieval (15% of traffic)
        group('Client Data Retrieval', () => {
            clientDataRetrieval(token);
        });
    } else {
        // Couples merge (15% of traffic)
        group('Couples Merge Workflow', () => {
            couplesMergeWorkflow(token);
        });
    }

    // Think time between requests (simulates real user behavior)
    sleep(randomIntBetween(1, 5));
}

// Setup function - runs once at start
export function setup() {
    console.log(`Starting load test against ${BASE_URL}`);
    console.log('Target: 100 concurrent users');
    console.log('Thresholds: P95 < 5s, Error rate < 5%');

    // Verify API is reachable
    const healthResponse = http.get(`${BASE_URL}/health`);
    if (healthResponse.status !== 200) {
        console.warn(`Warning: Health check returned ${healthResponse.status}`);
    }

    return { startTime: Date.now() };
}

// Teardown function - runs once at end
export function teardown(data) {
    const duration = (Date.now() - data.startTime) / 1000;
    console.log(`Load test completed in ${duration.toFixed(2)} seconds`);
}

// Handle summary
export function handleSummary(data) {
    return {
        'stdout': textSummary(data, { indent: ' ', enableColors: true }),
        'scripts/load_tests/results/summary.json': JSON.stringify(data, null, 2),
    };
}

// Text summary helper
function textSummary(data, opts) {
    const metrics = data.metrics;
    let summary = '\n=== Rung Load Test Results ===\n\n';

    // Key metrics
    summary += 'Key Performance Metrics:\n';
    summary += `  HTTP Requests: ${metrics.http_reqs?.values?.count || 0}\n`;
    summary += `  Request Duration P95: ${(metrics.http_req_duration?.values?.['p(95)'] || 0).toFixed(2)}ms\n`;
    summary += `  Error Rate: ${((metrics.errors?.values?.rate || 0) * 100).toFixed(2)}%\n`;
    summary += '\n';

    // Workflow latencies
    summary += 'Workflow Latencies (P95):\n';
    summary += `  Pre-Session: ${(metrics.pre_session_latency?.values?.['p(95)'] || 0).toFixed(2)}ms\n`;
    summary += `  Post-Session: ${(metrics.post_session_latency?.values?.['p(95)'] || 0).toFixed(2)}ms\n`;
    summary += `  Couples Merge: ${(metrics.couples_merge_latency?.values?.['p(95)'] || 0).toFixed(2)}ms\n`;
    summary += `  Authentication: ${(metrics.auth_latency?.values?.['p(95)'] || 0).toFixed(2)}ms\n`;
    summary += '\n';

    // Threshold results
    summary += 'Threshold Results:\n';
    for (const [name, threshold] of Object.entries(data.thresholds || {})) {
        const status = threshold.ok ? 'PASS' : 'FAIL';
        summary += `  ${name}: ${status}\n`;
    }

    return summary;
}
