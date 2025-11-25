#!/usr/bin/env python3
"""
Service key management script.

This script helps create and manage service API keys for internal services
like the Slack integration.
"""

import asyncio
import sys
from typing import Optional

from app.services.database import get_database


async def create_service_key(service_name: str) -> Optional[str]:
    """
    Create a new service API key.

    Args:
        service_name: Name of the service

    Returns:
        API key if successful, None otherwise
    """
    try:
        db = get_database()
        result = db.create_service_key(service_name)

        if result:
            api_key, service_info = result
            print(f"✅ Successfully created service key for: {service_name}")
            print(f"📝 Service ID: {service_info['id']}")
            print(f"🔑 API Key: {api_key}")
            print("\n⚠️  IMPORTANT: Save this API key securely - it won't be shown again!")
            print(f"   Add this to your {service_name} environment:")
            print(f"   SERVICE_API_KEY={api_key}")
            return api_key
        else:
            print(f"❌ Failed to create service key for: {service_name}")
            return None

    except Exception as e:
        print(f"❌ Error creating service key: {e}")
        return None


async def list_service_keys() -> None:
    """List all service keys."""
    try:
        db = get_database()
        service_keys = db.list_service_keys()

        if not service_keys:
            print("📋 No service keys found")
            return

        print(f"📋 Found {len(service_keys)} service key(s):")
        print("=" * 80)

        for service in service_keys:
            status = "🟢 Active" if service["is_active"] else "🔴 Inactive"
            last_used = service["last_used_at"] or "Never"

            print(f"Service: {service['service_name']}")
            print(f"  ID: {service['id']}")
            print(f"  Status: {status}")
            print(f"  Created: {service['created_at']}")
            print(f"  Last Used: {last_used}")
            print("-" * 40)

    except Exception as e:
        print(f"❌ Error listing service keys: {e}")


async def deactivate_service_key(service_name: str) -> bool:
    """
    Deactivate a service key.

    Args:
        service_name: Name of the service

    Returns:
        True if successful, False otherwise
    """
    try:
        db = get_database()
        success = db.deactivate_service_key(service_name)

        if success:
            print(f"✅ Successfully deactivated service key for: {service_name}")
            return True
        else:
            print(f"❌ Failed to deactivate service key for: {service_name}")
            return False

    except Exception as e:
        print(f"❌ Error deactivating service key: {e}")
        return False


def print_usage() -> None:
    """Print script usage information."""
    print("🔐 Service Key Management")
    print("=" * 50)
    print("Usage:")
    print("  python manage_service_keys.py create <service_name>")
    print("  python manage_service_keys.py list")
    print("  python manage_service_keys.py deactivate <service_name>")
    print()
    print("Examples:")
    print("  python manage_service_keys.py create slack-integration")
    print("  python manage_service_keys.py list")
    print("  python manage_service_keys.py deactivate slack-integration")


async def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "create":
        if len(sys.argv) != 3:
            print("❌ Error: service_name required")
            print("Usage: python manage_service_keys.py create <service_name>")
            sys.exit(1)

        service_name = sys.argv[2]
        await create_service_key(service_name)

    elif command == "list":
        await list_service_keys()

    elif command == "deactivate":
        if len(sys.argv) != 3:
            print("❌ Error: service_name required")
            print("Usage: python manage_service_keys.py deactivate <service_name>")
            sys.exit(1)

        service_name = sys.argv[2]
        await deactivate_service_key(service_name)

    else:
        print(f"❌ Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
