#!/usr/bin/env python3
"""Seed script to create default admin user."""
import asyncio
import bcrypt
from sqlalchemy import text
from backend.app.db.crm_db import get_async_crm_session


async def seed_admin_user():
    """Create default admin user if not exists."""
    email = "eddy@warroom.local"
    password = "admin123"
    name = "Eddy (Admin)"
    
    # Hash the password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    async with get_async_crm_session() as session:
        # Check if user already exists
        result = await session.execute(
            text("SELECT id FROM crm.users WHERE email = :email"),
            {"email": email}
        )
        existing_user = result.fetchone()
        
        if existing_user:
            print(f"Admin user {email} already exists")
            return
        
        # Create admin user
        await session.execute(
            text("""
                INSERT INTO crm.users (name, email, password_hash, status)
                VALUES (:name, :email, :password_hash, :status)
            """),
            {
                "name": name,
                "email": email,
                "password_hash": password_hash,
                "status": True
            }
        )
        await session.commit()
        print(f"Created admin user: {email} with password: {password}")


if __name__ == "__main__":
    asyncio.run(seed_admin_user())