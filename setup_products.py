#!/usr/bin/env python3
"""
Setup script to initialize AI Automation Services products
Run this after the database migration
"""

import asyncio
import sys
import os

# Add the backend app to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.crm_db import get_async_engine, AsyncSessionLocal
from backend.app.models.crm.product import Product


async def setup_products():
    """Create the AI Automation Services products."""
    print("Setting up AI Automation Services products...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Check if products already exist
            existing = await db.execute(
                "SELECT COUNT(*) FROM crm.products WHERE category = 'ai-automation'"
            )
            count = existing.scalar()
            
            if count > 0:
                print(f"Found {count} existing AI automation products. Skipping creation.")
                return
            
            # Create the three tiers
            products = [
                Product(
                    org_id=1,
                    sku="ALEC-STARTER",
                    name="AI Automation Starter (Foundation)",
                    description="Perfect for small businesses starting their AI journey",
                    price=99.00,
                    billing_interval="monthly",
                    features=[
                        "1 Managed OpenClaw Agent",
                        "1,000,000 Standard Tokens",
                        "24/7 Heartbeat (every 30 min)",
                        "WhatsApp or Telegram messaging",
                        "Email support (48h response)",
                        "First 100 Customers — Founding Member Pricing"
                    ],
                    is_active=True,
                    tier_level=1,
                    category="ai-automation",
                    quantity=999
                ),
                Product(
                    org_id=1,
                    sku="ALEC-PRO",
                    name="AI Automation Professional",
                    description="Ideal for growing businesses ready to scale automation",
                    price=299.00,
                    billing_interval="monthly",
                    features=[
                        "3 Dedicated OpenClaw Agents",
                        "5,000,000 Standard Tokens",
                        "24/7 Heartbeat (every 5 min)",
                        "WhatsApp + Discord + Slack messaging",
                        "Priority Slack support (12h response)",
                        "Advanced CRM orchestration",
                        "Custom business logic"
                    ],
                    is_active=True,
                    tier_level=2,
                    category="ai-automation",
                    quantity=999
                ),
                Product(
                    org_id=1,
                    sku="ALEC-ENTERPRISE",
                    name="AI Automation Enterprise",
                    description="Custom solution for enterprise-scale operations",
                    price=0.00,
                    billing_interval="custom",
                    features=[
                        "Unlimited OpenClaw Agents",
                        "Unlimited tokens / BYO API key",
                        "Real-time / custom heartbeat",
                        "All channels + API access",
                        "Dedicated AI Engineer"
                    ],
                    is_active=True,
                    tier_level=3,
                    category="ai-automation",
                    quantity=999
                )
            ]
            
            for product in products:
                db.add(product)
                print(f"Created product: {product.name}")
            
            await db.commit()
            print("✅ Successfully created AI Automation Services products!")
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error creating products: {e}")
            raise


async def main():
    """Main setup function."""
    print("🚀 Starting WAR ROOM Products Setup")
    
    try:
        # Run database migration first
        print("📦 Running database migration...")
        import subprocess
        result = subprocess.run([
            'psql', '-f', 'backend/app/db/product_tiers_migration.sql', 
            os.getenv('DATABASE_URL', 'postgresql://localhost/warroom')
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Database migration completed successfully")
        else:
            print(f"❌ Migration failed: {result.stderr}")
            return
        
        # Setup products
        await setup_products()
        
        print("\n🎉 Setup complete! You can now:")
        print("1. View products in the CRM Products panel")
        print("2. Create pricing pages with PricingDisplay component")
        print("3. Set up Stripe integration with the price IDs")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())