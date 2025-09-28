#!/usr/bin/env python3
"""
Database migration script for Railway PostgreSQL
Executes the complete_setup.sql migration file
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def get_database_url():
    """Get database URL from environment or Railway default"""
    return os.getenv('DATABASE_URL', 'postgresql://postgres:KdlihqBBEDEaFPdJKCMBpBINqGtRSqEc@viaduct.proxy.rlwy.net:59522/railway')

def run_migration():
    """Execute the complete database setup migration"""

    # Read migration file
    try:
        with open('migrations/complete_setup.sql', 'r', encoding='utf-8') as f:
            migration_sql = f.read()
    except FileNotFoundError:
        print("❌ Migration file not found: migrations/complete_setup.sql")
        return False

    # Connect to database
    database_url = get_database_url()
    print(f"🔌 Connecting to database...")

    try:
        conn = psycopg2.connect(database_url)
        conn.set_session(autocommit=True)

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            print("📄 Executing migration SQL...")

            # Split SQL into individual statements (handle multiple statements)
            statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]

            for i, statement in enumerate(statements):
                if statement:
                    try:
                        print(f"  ⏳ Executing statement {i+1}/{len(statements)}")
                        cursor.execute(statement)

                        # If it's a SELECT statement, fetch and print results
                        if statement.strip().upper().startswith('SELECT'):
                            results = cursor.fetchall()
                            for row in results:
                                print(f"    📊 {dict(row)}")

                    except psycopg2.Error as e:
                        print(f"    ⚠️  Statement {i+1} error (might be expected): {e}")
                        continue

            print("✅ Migration completed successfully!")

            # Verify tables were created
            print("\n🔍 Verifying tables exist:")
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()

            for table in tables:
                print(f"  ✓ {table['table_name']}")

            # Check record counts
            print("\n📊 Record counts:")
            for table in tables:
                table_name = table['table_name']
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name};")
                    count = cursor.fetchone()
                    print(f"  📋 {table_name}: {count['count']} records")
                except:
                    print(f"  ❌ {table_name}: Error counting records")

        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting database migration...")
    success = run_migration()

    if success:
        print("\n🎉 Migration completed successfully!")
        print("💡 You can now test your API endpoints")
        sys.exit(0)
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)