# test_inserts.py
from datetime import datetime, timezone
from supabase import create_client
from faker import Faker
import os
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

# Initialize Faker
fake = Faker()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not supabase_url or not supabase_key:
    print("❌ Error: Missing Supabase URL or key in .env file")
    exit(1)

print(f"URL: {supabase_url[:20]}...") 
print(f"Key: {supabase_key[:5]}...{supabase_key[-5:]}") 

supabase = create_client(supabase_url, supabase_key)

# Define table names matching the new schema
class Tables:
    ORGANIZATIONS = "organizations"
    ORGANIZATION_USERS = "organization_users"  # Updated to match new schema

def generate_test_data(org_count=2, users_per_org=2):
    """Generate test data for organizations and users"""
    organizations = []
    org_users = []
    
    print("\n📝 Generating test data...")
    
    # Generate organizations (don't specify ID - let PostgreSQL auto-assign)
    for i in range(org_count):
        org_name = f"Test Org {i+1} - {fake.company()}"
        domain = f"test-{i+1}-{fake.domain_word()}.com"
        
        org = {
            # Don't specify 'id' - let PostgreSQL auto-assign the serial integer
            "name": org_name,
            "domain": domain,  # Required field in new schema
            "website": f"https://{domain}",
            "country": fake.country(),
            "city": fake.city(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        organizations.append(org)
        print(f"   Generated organization: {org_name}")
    
    return {
        "organizations": organizations,
        "org_users": org_users  # We'll populate this after getting org IDs
    }

def insert_organizations(organizations):
    """Insert organizations and return their IDs"""
    print("\n🔄 Inserting organizations...")
    inserted_orgs = []
    
    for org in organizations:
        try:
            response = supabase.table(Tables.ORGANIZATIONS).insert(org).execute()
            if response.data and len(response.data) > 0:
                inserted_org = response.data[0]
                inserted_orgs.append(inserted_org)
                print(f"   ✅ Inserted: {org['name']} (ID: {inserted_org['id']})")
            else:
                print(f"   ⚠️ No data returned for: {org['name']}")
        except Exception as e:
            print(f"   ❌ Error inserting {org['name']}: {str(e)}")
    
    return inserted_orgs

def insert_organization_users(org_ids, users_per_org=2):
    """Insert organization-user relationships"""
    print("\n🔄 Inserting organization-user relationships...")
    success_count = 0
    
    for org_id in org_ids:
        for j in range(users_per_org):
            user_id = j + 1  # Simple integer user IDs for testing
            role_id = 1 if j == 0 else 2  # Assuming role_id 1 = admin, 2 = member
            
            org_user = {
                "org_id": org_id,
                "user_id": user_id,
                "role_id": role_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            try:
                response = supabase.table(Tables.ORGANIZATION_USERS).insert(org_user).execute()
                if response.data:
                    role_name = "admin" if role_id == 1 else "member"
                    print(f"   ✅ Inserted: User {user_id} as {role_name} in org {org_id}")
                    success_count += 1
                else:
                    print(f"   ⚠️ No data returned for user {user_id} in org {org_id}")
            except Exception as e:
                print(f"   ❌ Error inserting user {user_id} in org {org_id}: {str(e)}")
    
    return success_count

def verify_data_insertion():
    """Verify that data was inserted correctly"""
    print("\n🔍 Verifying data insertion...")
    
    try:
        # Check organizations
        org_response = supabase.table(Tables.ORGANIZATIONS).select("id, name, domain").limit(10).execute()
        
        if hasattr(org_response, 'data') and org_response.data:
            org_count = len(org_response.data)
            print(f"   ✅ Found {org_count} organizations in the database")
            
            print("\n   📋 Organizations:")
            for org in org_response.data:
                print(f"      ID: {org.get('id')} - Name: {org.get('name')} - Domain: {org.get('domain')}")
        else:
            print("   ❌ No organizations found")
        
        # Check organization users
        user_response = supabase.table(Tables.ORGANIZATION_USERS).select("org_id, user_id, role_id").limit(10).execute()
        
        if hasattr(user_response, 'data') and user_response.data:
            user_count = len(user_response.data)
            print(f"   ✅ Found {user_count} organization-user relationships in the database")
            
            print("\n   📋 Organization Users:")
            for user in user_response.data:
                role_name = "admin" if user.get('role_id') == 1 else "member"
                print(f"      User ID: {user.get('user_id')} - Role: {role_name} in Org: {user.get('org_id')}")
        else:
            print("   ❌ No organization-user relationships found")
            
        return True
    except Exception as e:
        print(f"   ❌ Error verifying data: {str(e)}")
        return False

def verify_table_names():
    """Verify the exact table names in the database"""
    print("\n🔍 Verifying exact table names in database...")
    
    try:
        # Query information_schema to get table names
        response = supabase.rpc('get_table_names').execute()
        
        if hasattr(response, 'data'):
            print(f"   ✅ Tables query executed")
            return True
        else:
            # Fallback: try to query the tables directly
            print("   ⚠️ Using fallback table verification...")
            
            # Test organizations table
            try:
                org_test = supabase.table(Tables.ORGANIZATIONS).select("id").limit(1).execute()
                print(f"   ✅ Table '{Tables.ORGANIZATIONS}' exists and is accessible")
            except Exception as e:
                print(f"   ❌ Table '{Tables.ORGANIZATIONS}' issue: {str(e)}")
            
            # Test organization_users table
            try:
                user_test = supabase.table(Tables.ORGANIZATION_USERS).select("org_id").limit(1).execute()
                print(f"   ✅ Table '{Tables.ORGANIZATION_USERS}' exists and is accessible")
            except Exception as e:
                print(f"   ❌ Table '{Tables.ORGANIZATION_USERS}' issue: {str(e)}")
            
            return True
    except Exception as e:
        print(f"   ❌ Error verifying table names: {str(e)}")
        return False

def create_test_users():
    """Create some test users in the users table"""
    print("\n🔄 Creating test users...")
    
    users = [
        {
            "id": 1,
            "email": "admin@test.com",
            "name": "Test Admin",
            "email_verified": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": 2,
            "email": "user@test.com", 
            "name": "Test User",
            "email_verified": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    for user in users:
        try:
            # Try to insert, ignore if already exists
            response = supabase.table("users").upsert(user).execute()
            if response.data:
                print(f"   ✅ Created/Updated user: {user['email']} (ID: {user['id']})")
        except Exception as e:
            print(f"   ⚠️ User {user['email']} might already exist: {str(e)}")

def main():
    print("🚀 Starting database insertion test for new schema...\n")

    # Verify table access
    if not verify_table_names():
        print("❌ Cannot verify tables. Exiting...")
        return

    # Create test users first
    create_test_users()
    
    # Generate test data
    test_data = generate_test_data(org_count=3, users_per_org=2)
    
    # Insert organizations and get their actual IDs
    inserted_orgs = insert_organizations(test_data["organizations"])
    
    if not inserted_orgs:
        print("❌ No organizations were inserted. Cannot continue.")
        return
    
    # Get the org IDs that were actually assigned
    org_ids = [org['id'] for org in inserted_orgs]
    print(f"\n📋 Inserted organization IDs: {org_ids}")
    
    # Insert organization-user relationships
    user_success_count = insert_organization_users(org_ids, users_per_org=2)
    
    # Show summary
    print("\n📊 Test Results Summary:")
    print(f"   ✅ Organizations inserted: {len(inserted_orgs)}")
    print(f"   ✅ Organization-user relationships inserted: {user_success_count}")
    
    # Verify insertions
    verify_data_insertion()
    
    print(f"\n🎯 You can now test with org_id: {org_ids[0]} (first organization)")
    print("\n🏁 Test completed!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        print("\nTraceback:")
        traceback.print_exc()