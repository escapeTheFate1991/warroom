#!/usr/bin/env bun

/**
 * Frontend API Contract Validator
 * 
 * Validates TypeScript interfaces against actual API responses to catch field name mismatches.
 * Run this to verify AI Studio components won't crash due to API contract violations.
 */

import { z } from 'zod';

// Base configuration
const API_BASE = 'http://localhost:8300';
const JWT_SECRET = 'cd33654a256f32c697fedce4f8fe6736d358e0e55eb2fbd452cece3f8ced5071';

// Generate test JWT token
function generateTestToken(): string {
  const payload = {
    user_id: 9,
    org_id: 1,
    exp: Math.floor(Date.now() / 1000) + 3600 // 1 hour
  };
  
  // Simple JWT implementation for testing
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payloadStr = btoa(JSON.stringify(payload));
  
  // Note: This is a simplified JWT for testing. In production, use a proper JWT library.
  return `${header}.${payloadStr}.signature`;
}

function getTestHeaders(): HeadersInit {
  return {
    'Authorization': `Bearer ${generateTestToken()}`,
    'Referer': 'http://localhost:3000',
    'Content-Type': 'application/json'
  };
}

// Define expected schemas based on frontend TypeScript interfaces
const QualityAuditSchema = z.object({
  total_images: z.number(),
  target_images: z.number(), 
  quality_ok: z.boolean(),
  angle_coverage: z.object({
    close_up: z.number(),
    full_body: z.number(),
    quarter_body: z.number(),
    profile_left: z.number(),
    profile_right: z.number(),
    other: z.number()
  }),
  missing_angles: z.array(z.string()),
  avg_resolution: z.object({
    width: z.number(),
    height: z.number()
  }),
  ready_for_training: z.boolean(),
  recommendation: z.string()
});

const DigitalCopySchema = z.object({
  id: z.number(),
  name: z.string(),
  trigger_token: z.string(),
  status: z.string(),
  images: z.array(z.object({
    id: z.number(),
    image_url: z.string(),
    image_type: z.string()
  }))
});

const VideoFormatSchema = z.object({
  slug: z.string(),
  name: z.string(),
  description: z.string().optional()
});

const HookScoreSchema = z.object({
  score: z.number().min(1).max(10)
});

const ProjectResponseSchema = z.object({
  project_id: z.union([z.number(), z.string()])
});

interface ValidationResult {
  endpoint: string;
  method: string;
  success: boolean;
  error?: string;
  missingFields?: string[];
  extraFields?: string[];
}

class APIValidator {
  private results: ValidationResult[] = [];

  async validateEndpoint(
    method: 'GET' | 'POST',
    path: string,
    schema: z.ZodSchema,
    payload?: any,
    description?: string
  ): Promise<void> {
    const url = `${API_BASE}${path}`;
    const result: ValidationResult = {
      endpoint: `${method} ${path}`,
      method,
      success: false
    };

    try {
      const options: RequestInit = {
        method,
        headers: getTestHeaders()
      };

      if (payload && method === 'POST') {
        options.body = JSON.stringify(payload);
      }

      console.log(`Testing ${method} ${path}${description ? ` - ${description}` : ''}`);
      
      const response = await fetch(url, options);
      
      if (!response.ok) {
        result.error = `HTTP ${response.status}: ${response.statusText}`;
        this.results.push(result);
        return;
      }

      const data = await response.json();
      
      // Validate against schema
      const parseResult = schema.safeParse(data);
      
      if (parseResult.success) {
        result.success = true;
        console.log(`✅ ${result.endpoint} - Schema validation passed`);
      } else {
        result.error = `Schema validation failed: ${parseResult.error.message}`;
        result.missingFields = parseResult.error.issues
          .filter(issue => issue.code === 'invalid_type' && issue.received === 'undefined')
          .map(issue => issue.path.join('.'));
        console.log(`❌ ${result.endpoint} - Schema validation failed`);
        console.log(`   Error: ${result.error}`);
      }

    } catch (error) {
      result.error = `Request failed: ${error instanceof Error ? error.message : String(error)}`;
      console.log(`💥 ${result.endpoint} - Request failed: ${result.error}`);
    }

    this.results.push(result);
  }

  async runAllTests(): Promise<void> {
    console.log('🚀 Starting AI Studio API Contract Validation\n');

    // Test Video Formats API
    console.log('📹 Testing Video Formats API...');
    await this.validateEndpoint('GET', '/api/video-formats', z.array(VideoFormatSchema), undefined, 'List formats');

    // Test Content Intelligence API  
    console.log('\n🧠 Testing Content Intelligence API...');
    await this.validateEndpoint(
      'POST', 
      '/api/content-intel/score-hook', 
      HookScoreSchema,
      { hook: 'Test hook for scoring' },
      'Score hook'
    );

    await this.validateEndpoint('GET', '/api/ai-studio/ugc/competitor-hooks', z.array(z.any()), undefined, 'Get competitor hooks');

    await this.validateEndpoint(
      'POST',
      '/api/ai-studio/ugc/generate-script',
      z.object({ script: z.string() }),
      {
        hook: 'Test hook',
        format_slug: 'talking-head',
        audience: 'entrepreneurs'
      },
      'Generate script'
    );

    await this.validateEndpoint('GET', '/api/content-intel/performance-dashboard', z.any(), undefined, 'Performance dashboard');
    await this.validateEndpoint('GET', '/api/content-intel/emerging-formats', z.array(z.any()), undefined, 'Emerging formats');

    // Test Video Project API
    console.log('\n🎬 Testing Video Project API...');
    await this.validateEndpoint(
      'POST',
      '/api/video/compose-from-scenes',
      ProjectResponseSchema,
      {
        scenes: [{ type: 'talking_head', duration: 5.0, script: 'Test scene' }],
        format_slug: 'talking-head'
      },
      'Compose from scenes'
    );

    await this.validateEndpoint(
      'POST',
      '/api/ai-studio/ugc/generate-voiceover',
      z.object({ audio_url: z.string() }),
      {
        text: 'Test voiceover text',
        voice: 'en-US-StudioNeural'
      },
      'Generate voiceover'
    );

    // Test Digital Copies API (the main bug area)
    console.log('\n👤 Testing Digital Copies API...');
    await this.validateEndpoint('GET', '/api/digital-copies', z.array(DigitalCopySchema), undefined, 'List digital copies');

    let testCopyId: number | null = null;

    // Create a test digital copy for further testing
    try {
      const createResponse = await fetch(`${API_BASE}/api/digital-copies`, {
        method: 'POST',
        headers: getTestHeaders(),
        body: JSON.stringify({
          name: 'Test Character for Validation',
          base_model: 'veo_3.1'
        })
      });

      if (createResponse.ok) {
        const createData = await createResponse.json();
        testCopyId = createData.id;
        console.log(`📝 Created test digital copy with ID: ${testCopyId}`);
      }
    } catch (error) {
      console.log('⚠️  Could not create test digital copy for further testing');
    }

    if (testCopyId) {
      // Test the quality audit endpoint (this was the main bug)
      await this.validateEndpoint(
        'GET',
        `/api/digital-copies/${testCopyId}/quality-audit`,
        QualityAuditSchema,
        undefined,
        'Quality audit (was buggy)'
      );
    }

    await this.validateEndpoint('GET', '/api/action-templates', z.array(z.any()), undefined, 'Action templates');

    if (testCopyId) {
      // Test build prompt (requires both digital copy and action template)
      try {
        const templatesResponse = await fetch(`${API_BASE}/api/action-templates`, {
          headers: getTestHeaders()
        });
        
        if (templatesResponse.ok) {
          const templates = await templatesResponse.json();
          if (templates.length > 0) {
            await this.validateEndpoint(
              'POST',
              `/api/digital-copies/${testCopyId}/build-prompt`,
              z.object({
                prompt: z.string(),
                negative_prompt: z.string(),
                character_token: z.string()
              }),
              {
                scene_description: 'Test scene description',
                action_template_slug: templates[0].slug
              },
              'Build prompt'
            );
          }
        }
      } catch (error) {
        console.log('⚠️  Could not test build-prompt endpoint');
      }
    }

    // Test Content Scheduler API
    console.log('\n📅 Testing Content Scheduler API...');
    await this.validateEndpoint(
      'POST',
      '/api/scheduler/smart-distribute',
      z.object({ distribution_id: z.union([z.number(), z.string()]) }),
      {
        content_type: 'video',
        priority: 'high',
        target_accounts: ['facebook'],
        schedule_preference: 'optimal'
      },
      'Smart distribute'
    );

    // Test Simulation API
    console.log('\n🎭 Testing Simulation API...');
    await this.validateEndpoint('GET', '/api/simulate/personas', z.array(z.any()), undefined, 'List personas');

    await this.validateEndpoint(
      'POST',
      '/api/simulate/social-friction-test',
      z.any(), // Schema will depend on actual implementation
      {
        content: 'Test content for simulation',
        platform: 'twitter',
        target_audience: 'entrepreneurs'
      },
      'Social friction test'
    );

    // Clean up test data
    if (testCopyId) {
      try {
        await fetch(`${API_BASE}/api/digital-copies/${testCopyId}`, {
          method: 'DELETE',
          headers: getTestHeaders()
        });
        console.log(`🗑️  Cleaned up test digital copy ${testCopyId}`);
      } catch (error) {
        console.log('⚠️  Could not clean up test digital copy');
      }
    }

    this.printSummary();
  }

  private printSummary(): void {
    console.log('\n' + '='.repeat(60));
    console.log('📊 VALIDATION SUMMARY');
    console.log('='.repeat(60));

    const passed = this.results.filter(r => r.success).length;
    const failed = this.results.filter(r => !r.success).length;
    
    console.log(`Total Tests: ${this.results.length}`);
    console.log(`✅ Passed: ${passed}`);
    console.log(`❌ Failed: ${failed}`);
    
    if (failed > 0) {
      console.log('\n💥 FAILED TESTS:');
      this.results
        .filter(r => !r.success)
        .forEach(result => {
          console.log(`\n${result.endpoint}:`);
          console.log(`  Error: ${result.error}`);
          if (result.missingFields?.length) {
            console.log(`  Missing Fields: ${result.missingFields.join(', ')}`);
          }
        });

      console.log('\n🔧 COMMON FIXES:');
      console.log('1. Check field name mismatches between frontend and backend');
      console.log('2. Verify TypeScript interfaces match API response schemas');
      console.log('3. Ensure all endpoints are implemented and accessible');
      console.log('4. Check authentication and CSRF protection');
    } else {
      console.log('\n🎉 All tests passed! AI Studio APIs are working correctly.');
    }

    console.log('='.repeat(60));

    // Exit with error code if any tests failed
    if (failed > 0) {
      process.exit(1);
    }
  }
}

// Run the validation
const validator = new APIValidator();
validator.runAllTests().catch(error => {
  console.error('💥 Validation script failed:', error);
  process.exit(1);
});