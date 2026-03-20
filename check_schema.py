#!/usr/bin/env python3
import asyncio
import asyncpg

async def check_schema():
    conn = await asyncpg.connect('postgresql://friday:friday-brain2-2026@10.0.0.11:5433/knowledge')
    
    # Check if the new columns exist
    columns = await conn.fetch("""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns 
        WHERE table_schema = 'crm' 
          AND table_name = 'products' 
          AND column_name IN ('billing_interval', 'features', 'stripe_price_id', 'is_active', 'tier_level', 'category')
        ORDER BY column_name
    """)
    
    print('Product table columns:', [col['column_name'] for col in columns])
    
    # Check if products exist
    products = await conn.fetch("SELECT name, category, tier_level, price FROM crm.products WHERE category = 'ai-automation' ORDER BY tier_level")
    print(f'AI automation products: {len(products)}')
    for product in products:
        name = product['name']
        tier = product['tier_level']
        price = product['price']
        print(f'  - {name} (Tier {tier}): ${price}')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_schema())