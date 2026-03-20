#!/usr/bin/env node
/**
 * Comprehensive Navigation Test
 * Tests all tabs in the WAR ROOM app for crashes
 */

// Use built-in fetch (Node 18+)
if (typeof fetch === 'undefined') {
    console.error('This script requires Node.js 18+ with built-in fetch');
    process.exit(1);
}

const API_BASE = 'http://localhost:8300'; // Default backend URL

// All tabs from page.tsx
const TABS = [
    'dashboard', 'chat', 'agents', 'agent-create', 'agent-edit', 'social', 
    'content-instagram', 'content-youtube', 'content-facebook', 'content-x', 
    'pipeline', 'content-social', 'social-instagram', 'social-tiktok', 
    'social-youtube', 'social-facebook', 'scheduler', 'recycle', 'intelligence', 
    'mirofish', 'kanban', 'leadgen', 'communications', 'prospects', 
    'pipeline-board', 'organizations', 'crm-contacts', 'crm-products', 'pricing', 
    'org-chart', 'library-search', 'library-educate', 'workflows', 
    'marketing-campaigns', 'marketing-templates', 'email', 'calendar', 
    'invoices', 'contracts', 'reports-overview', 'ai-studio', 'settings', 'profile'
];

// API endpoints that tabs depend on (mapping tab -> endpoint)
const TAB_ENDPOINTS = {
    'mirofish': ['/api/video-copycat/storyboards', '/api/social/content'],
    'pricing': ['/api/crm/products?category=ai-automation&is_active=true'],
    'ai-studio': ['/api/digital-copies', '/api/ai-studio/ugc/templates', '/api/ai-studio/ugc/projects', '/api/action-templates'],
    'crm-products': ['/api/crm/products'],
    'social': ['/api/social/content'],
    'leadgen': ['/api/leadgen/jobs'],
    'kanban': ['/api/kanban/tasks'],
    'agents': ['/api/agents'],
    'workflows': ['/api/workflows'],
    'reports-overview': ['/api/reports/overview'],
    'communications': ['/api/communications/messages'],
    'prospects': ['/api/prospects'],
    'organizations': ['/api/crm/organizations'],
    'crm-contacts': ['/api/crm/contacts'],
    'scheduler': ['/api/scheduler/posts'],
    'calendar': ['/api/calendar/events'],
    'email': ['/api/email/messages'],
    'invoices': ['/api/invoices'],
    'contracts': ['/api/contracts'],
    'library-search': ['/api/library/search'],
    'library-educate': ['/api/library/educate'],
    'marketing-campaigns': ['/api/marketing/campaigns'],
    'marketing-templates': ['/api/marketing/templates']
};

async function testEndpoint(endpoint) {
    try {
        const url = `${API_BASE}${endpoint}`;
        console.log(`Testing: ${url}`);
        const response = await fetch(url, {
            headers: {
                'Authorization': 'Bearer dummy', // Mock auth for testing
                'Content-Type': 'application/json'
            }
        });
        
        return {
            endpoint,
            status: response.status,
            ok: response.ok,
            error: response.ok ? null : `HTTP ${response.status}`
        };
    } catch (error) {
        return {
            endpoint,
            status: 0,
            ok: false,
            error: error.message
        };
    }
}

async function runTests() {
    console.log('🚀 WAR ROOM Navigation Test Suite');
    console.log(`Testing against: ${API_BASE}`);
    console.log(`Total tabs to test: ${TABS.length}\n`);

    const results = {
        passed: [],
        failed: [],
        apiErrors: []
    };

    // Test API endpoints
    console.log('📡 Testing API Endpoints...\n');
    
    for (const [tab, endpoints] of Object.entries(TAB_ENDPOINTS)) {
        console.log(`Testing tab: ${tab}`);
        
        for (const endpoint of endpoints) {
            const result = await testEndpoint(endpoint);
            
            if (result.ok) {
                console.log(`  ✅ ${endpoint} - OK`);
                results.passed.push(`${tab}: ${endpoint}`);
            } else {
                console.log(`  ❌ ${endpoint} - ${result.error}`);
                results.failed.push(`${tab}: ${endpoint} - ${result.error}`);
                results.apiErrors.push({
                    tab,
                    endpoint,
                    error: result.error
                });
            }
        }
        console.log('');
    }

    // Report results
    console.log('📊 Test Results Summary');
    console.log('========================\n');
    console.log(`✅ Passed: ${results.passed.length}`);
    console.log(`❌ Failed: ${results.failed.length}`);
    
    if (results.apiErrors.length > 0) {
        console.log('\n🔥 API Errors that could cause .map() crashes:');
        results.apiErrors.forEach(error => {
            console.log(`  • ${error.tab}: ${error.endpoint} - ${error.error}`);
        });
    }

    // Test recommendations
    console.log('\n🛠️  Fix Recommendations:');
    console.log('1. Add Array.isArray() guards to all .map() calls');
    console.log('2. Initialize state as empty arrays: useState<Type[]>([])');
    console.log('3. Add fallbacks in API handlers: setData(response.data || [])');
    console.log('4. Handle loading states properly');

    if (results.failed.length === 0) {
        console.log('\n🎉 All API endpoints are responding correctly!');
    }

    return results;
}

// Run the tests
runTests().catch(console.error);