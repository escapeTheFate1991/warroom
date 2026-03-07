#!/usr/bin/env python3
"""Seed script to create default admin user.

Requires ADMIN_PASSWORD environment variable (or set in .env).
"""
import asyncio
import os
import sys

import bcrypt
from sqlalchemy import text
from backend.app.db.crm_db import get_async_crm_session


async def seed_admin_user():
    """Create default admin user if not exists."""
    email = "eddy@warroom.local"
    name = "Eddy (Admin)"

    password = os.getenv("ADMIN_PASSWORD", "").strip()
    if not password:
        print("ERROR: ADMIN_PASSWORD environment variable is required.", file=sys.stderr)
        print("Set it in your .env file or pass it inline:", file=sys.stderr)
        print("  ADMIN_PASSWORD=your-secure-password python seed_admin.py", file=sys.stderr)
        sys.exit(1)

    if len(password) < 8:
        print("ERROR: ADMIN_PASSWORD must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

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
        print(f"Created admin user: {email}")


if __name__ == "__main__":
    asyncio.run(seed_admin_user())