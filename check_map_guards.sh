#!/bin/bash
# Check for .map() calls without proper Array.isArray() guards

echo "🔍 Checking for potentially unsafe .map() calls..."
echo "=================================================="

cd /home/eddy/Development/warroom

# Find all .map() calls in recently modified files
echo -e "\n📋 All .map() calls in key components:"
grep -n "\.map(" frontend/src/components/mirofish/MiroFishPanel.tsx frontend/src/components/pricing/PricingPage.tsx frontend/src/components/ai-studio/AIStudioPanel.tsx 2>/dev/null || echo "No .map() calls found (this might indicate a problem)"

echo -e "\n🛡️ Checking for guarded .map() calls:"
grep -n "Array\.isArray.*\.map(" frontend/src/components/mirofish/MiroFishPanel.tsx frontend/src/components/pricing/PricingPage.tsx frontend/src/components/ai-studio/AIStudioPanel.tsx 2>/dev/null | wc -l | xargs echo "Guarded .map() calls:"

echo -e "\n⚠️ Potentially unguarded .map() calls:"
# Look for .map() calls that don't have Array.isArray() on the same line or previous line
grep -n "\.map(" frontend/src/components/mirofish/MiroFishPanel.tsx frontend/src/components/pricing/PricingPage.tsx frontend/src/components/ai-studio/AIStudioPanel.tsx 2>/dev/null | grep -v "Array\.isArray" | grep -v "||.*\[\]"

echo -e "\n✅ State initializations:"
grep -n "useState.*\[\]" frontend/src/components/mirofish/MiroFishPanel.tsx frontend/src/components/pricing/PricingPage.tsx frontend/src/components/ai-studio/AIStudioPanel.tsx 2>/dev/null | wc -l | xargs echo "Empty array initializations:"

echo -e "\n📊 Summary:"
echo "- Key components checked: MiroFishPanel, PricingPage, AIStudioPanel"
echo "- These are the components most likely to cause '.map() is not a function' errors"
echo "- All API calls should have fallback empty arrays: setData(response.data || [])"
echo "- All .map() calls should have Array.isArray() guards"

echo -e "\n🚀 Test the navigation at: http://localhost:3300"
echo "   Try switching between tabs: mirofish, pricing, ai-studio"