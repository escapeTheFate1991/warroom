#!/usr/bin/env python3
"""Wave 2 Batch Executor - Run intent classification and CDR generation

Executes the batch operations via API endpoints:
1. Batch classify all 857 posts
2. Get CDR candidates (Power Score > 2000)  
3. Generate CDRs for top 10 posts
4. Verify output quality
"""

import asyncio
import json
import time
import httpx
import jwt
from datetime import datetime, timezone
from typing import Dict, List, Any

# Configuration
BASE_URL = "http://localhost:8300"
JWT_SECRET = "cd33654a256f32c697fedce4f8fe6736d358e0e55eb2fbd452cece3f8ced5071"

def generate_auth_token() -> str:
    """Generate JWT token for API authentication"""
    payload = {
        "user_id": 9,
        "org_id": 1,
        "exp": datetime.now(timezone.utc).timestamp() + 3600
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def get_headers() -> Dict[str, str]:
    """Get authentication headers"""
    token = generate_auth_token()
    return {
        "Authorization": f"Bearer {token}",
        "Referer": "http://localhost:3000",
        "Content-Type": "application/json"
    }

async def step_1_batch_classify():
    """Step 1: Run batch intent classification on all posts"""
    print("🔄 Step 1: Running batch intent classification...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/content-intel/classify-intents/batch",
                headers=get_headers(),
                json={}  # No filters - process all posts
            )
            
            if response.status_code != 200:
                print(f"❌ Batch classification failed: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
            result = response.json()
            
            print(f"✅ Batch classification completed:")
            print(f"   - Processed: {result.get('processed', 0)} posts")
            print(f"   - Errors: {result.get('errors', 0)}")
            print(f"   - CDR Candidates: {result.get('cdr_candidates', 0)}")
            print(f"   - High Priority: {result.get('high_priority', 0)}")
            print(f"   - Avg Power Score: {result.get('avg_power_score', 0)}")
            
            return result
            
        except Exception as e:
            print(f"❌ Batch classification error: {e}")
            return None

async def step_2_get_cdr_candidates():
    """Step 2: Get CDR candidates (Power Score > 2000)"""
    print("\n🔄 Step 2: Getting CDR candidates...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(
                f"{BASE_URL}/api/content-intel/cdr-candidates",
                headers=get_headers()
            )
            
            if response.status_code != 200:
                print(f"❌ CDR candidates fetch failed: {response.status_code}")
                print(f"Response: {response.text}")
                return []
                
            candidates = response.json()
            
            print(f"✅ Found {len(candidates)} CDR candidates:")
            for i, candidate in enumerate(candidates[:10]):  # Show top 10
                print(f"   {i+1}. Post #{candidate['id']}: {candidate['power_score']:.0f} power score")
                print(f"      Intent: {candidate['dominant_intent']} | Priority: {candidate['action_priority']}")
            
            return candidates
            
        except Exception as e:
            print(f"❌ CDR candidates error: {e}")
            return []

async def step_3_generate_cdrs(candidates: List[Dict]):
    """Step 3: Generate CDRs for top 10 highest scoring posts"""
    print("\n🔄 Step 3: Generating CDRs for top performers...")
    
    if not candidates:
        print("❌ No candidates available for CDR generation")
        return []
    
    # Take top 10 by power score
    top_candidates = sorted(candidates, key=lambda x: x['power_score'], reverse=True)[:10]
    generated_cdrs = []
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, candidate in enumerate(top_candidates):
            post_id = candidate['id']
            power_score = candidate['power_score']
            
            print(f"   Generating CDR {i+1}/10 for Post #{post_id} (Power: {power_score:.0f})...")
            
            try:
                response = await client.post(
                    f"{BASE_URL}/api/content-intel/creator-directive/{post_id}",
                    headers=get_headers(),
                    json={}
                )
                
                if response.status_code != 200:
                    print(f"   ❌ CDR generation failed for Post #{post_id}: {response.status_code}")
                    print(f"   Response: {response.text}")
                    continue
                    
                cdr_result = response.json()
                generated_cdrs.append({
                    "post_id": post_id,
                    "power_score": power_score,
                    "cdr": cdr_result
                })
                
                print(f"   ✅ CDR generated for Post #{post_id}")
                
            except Exception as e:
                print(f"   ❌ CDR generation error for Post #{post_id}: {e}")
                continue
    
    print(f"✅ Generated {len(generated_cdrs)} CDRs successfully")
    return generated_cdrs

def step_4_verify_cdr_quality(generated_cdrs: List[Dict]):
    """Step 4: Verify CDR output quality - all 5 sections present"""
    print("\n🔄 Step 4: Verifying CDR quality...")
    
    required_sections = [
        "hook_directive",
        "retention_blueprint", 
        "share_catalyst",
        "conversion_close",
        "technical_specs"
    ]
    
    valid_cdrs = 0
    detailed_output = []
    
    for cdr_data in generated_cdrs:
        post_id = cdr_data['post_id']
        power_score = cdr_data['power_score']
        cdr = cdr_data['cdr']
        
        print(f"\n📊 CDR Quality Check - Post #{post_id} (Power: {power_score:.0f})")
        
        missing_sections = []
        present_sections = []
        
        for section in required_sections:
            if section in cdr and cdr[section]:
                present_sections.append(section)
                print(f"   ✅ {section}")
            else:
                missing_sections.append(section)
                print(f"   ❌ {section} - MISSING")
        
        if not missing_sections:
            valid_cdrs += 1
            print(f"   🎯 Quality: EXCELLENT - All sections present")
        elif len(missing_sections) <= 1:
            print(f"   ⚠️  Quality: GOOD - {len(missing_sections)} missing section(s)")
        else:
            print(f"   ❌ Quality: POOR - {len(missing_sections)} missing sections")
        
        # Store for detailed output
        detailed_output.append({
            "post_id": post_id,
            "power_score": power_score,
            "sections_present": len(present_sections),
            "sections_missing": missing_sections,
            "cdr": cdr
        })
    
    print(f"\n📈 CDR Quality Summary:")
    print(f"   - Total CDRs: {len(generated_cdrs)}")
    print(f"   - Fully Valid: {valid_cdrs}")
    print(f"   - Success Rate: {(valid_cdrs/len(generated_cdrs)*100):.1f}%" if generated_cdrs else "0%")
    
    return detailed_output

def step_5_show_sample_outputs(detailed_output: List[Dict]):
    """Step 5: Show actual CDR output for top 3 posts as proof"""
    print("\n🔄 Step 5: Sample CDR Outputs (Proof of Completion)")
    
    # Show top 3 by power score
    samples = sorted(detailed_output, key=lambda x: x['power_score'], reverse=True)[:3]
    
    for i, sample in enumerate(samples):
        post_id = sample['post_id']
        power_score = sample['power_score']
        cdr = sample['cdr']
        
        print(f"\n{'='*60}")
        print(f"📋 SAMPLE CDR #{i+1} - Post #{post_id} (Power Score: {power_score:.0f})")
        print(f"{'='*60}")
        
        # Hook Directive
        if 'hook_directive' in cdr:
            hook = cdr['hook_directive']
            print(f"\n🎯 HOOK DIRECTIVE:")
            print(f"   Visual: {hook.get('visual', 'N/A')[:100]}...")
            print(f"   Script: {hook.get('script_line', 'N/A')[:100]}...")
            print(f"   Overlay: {hook.get('overlay', 'N/A')[:100]}...")
        
        # Retention Blueprint  
        if 'retention_blueprint' in cdr:
            retention = cdr['retention_blueprint']
            print(f"\n⏱️ RETENTION BLUEPRINT:")
            pacing = retention.get('pacing_rules', [])
            if pacing:
                print(f"   Pacing: {pacing[0][:80]}..." if pacing[0] else "N/A")
            interrupts = retention.get('pattern_interrupts', [])
            if interrupts:
                print(f"   Interrupts: {interrupts[0][:80]}..." if interrupts[0] else "N/A")
        
        # Share Catalyst
        if 'share_catalyst' in cdr:
            share = cdr['share_catalyst'] 
            print(f"\n🚀 SHARE CATALYST:")
            print(f"   Identity Moment: {share.get('identity_moment', 'N/A')[:100]}...")
            print(f"   Timestamp: {share.get('timestamp', 'N/A')}")
        
        # Conversion Close
        if 'conversion_close' in cdr:
            conversion = cdr['conversion_close']
            print(f"\n💰 CONVERSION CLOSE:")
            print(f"   CTA Type: {conversion.get('cta_type', 'N/A')}")
            print(f"   Script: {conversion.get('script_line', 'N/A')[:100]}...")
        
        # Technical Specs
        if 'technical_specs' in cdr:
            tech = cdr['technical_specs']
            print(f"\n🎥 TECHNICAL SPECS:")
            print(f"   Length: {tech.get('video_length', 'N/A')}")
            print(f"   Lighting: {tech.get('lighting', 'N/A')[:80]}...")
            print(f"   Music: {tech.get('music_bpm', 'N/A')}")
        
        # Generator Prompts
        if 'generator_prompts' in cdr:
            prompts = cdr['generator_prompts']
            print(f"\n🤖 GENERATOR PROMPTS:")
            veo_prompt = prompts.get('veo_prompt', 'N/A')
            print(f"   Veo: {veo_prompt[:120]}..." if len(veo_prompt) > 120 else f"   Veo: {veo_prompt}")
        
        print(f"\n{'='*60}")

async def main():
    """Execute complete Wave 2 batch processing pipeline"""
    print("🚀 Wave 2 Batch Processing - Intent Classification & CDR Generation")
    print("="*70)
    
    start_time = time.time()
    
    try:
        # Step 1: Batch classify all posts
        batch_result = await step_1_batch_classify()
        if not batch_result:
            print("❌ Pipeline failed at Step 1 - Classification")
            return
        
        # Step 2: Get CDR candidates
        candidates = await step_2_get_cdr_candidates()
        if not candidates:
            print("❌ Pipeline failed at Step 2 - No candidates found")
            return
        
        # Step 3: Generate CDRs for top performers
        generated_cdrs = await step_3_generate_cdrs(candidates)
        if not generated_cdrs:
            print("❌ Pipeline failed at Step 3 - No CDRs generated")
            return
        
        # Step 4: Verify CDR quality
        detailed_output = step_4_verify_cdr_quality(generated_cdrs)
        
        # Step 5: Show sample outputs as proof
        step_5_show_sample_outputs(detailed_output)
        
        # Final summary
        elapsed_time = time.time() - start_time
        print(f"\n🎉 Wave 2 Batch Processing COMPLETED!")
        print(f"⏱️  Total Time: {elapsed_time:.1f} seconds")
        print(f"📊 Results Summary:")
        print(f"   - Posts Classified: {batch_result.get('processed', 0)}")
        print(f"   - CDR Candidates: {len(candidates)}")
        print(f"   - CDRs Generated: {len(generated_cdrs)}")
        print(f"   - Avg Power Score: {batch_result.get('avg_power_score', 0)}")
        
        print(f"\n✅ Frontend now has real data to display in Wave 2 UI!")
        
    except KeyboardInterrupt:
        print("\n⏸️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(main())