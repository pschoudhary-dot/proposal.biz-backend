# test_inserts.py
import uuid
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

# Print partial values for verification without exposing sensitive data
print(f"URL: {supabase_url[:20]}...") 
print(f"Key: {supabase_key[:5]}...{supabase_key[-5:]}") 

supabase = create_client(supabase_url, supabase_key)

# Define table names - ensure these match EXACTLY with your database
# Postgres table names are typically lowercase unless created with quotes
class Tables:
    ORGANIZATIONS = "organizations"
    ORG_USERS = "orgusers"  # Most likely lowercase in the actual database

def add_permissive_policies():
    """Ensure permissive insert policies exist"""
    try:
        print("🔄 Adding permissive insert policies...")
        response = supabase.rpc('add_test_insert_policies').execute()
        print("✅ Permissive policies added successfully")
        return True
    except Exception as e:
        print(f"❌ Error adding permissive policies: {e}")
        return False

def generate_test_data(org_count=2, users_per_org=2):
    """Generate test data for organizations and users"""
    organizations = []
    users = []
    org_users = []
    
    print("\n📝 Generating test data...")
    
    # Generate organizations
    for i in range(org_count):
        org_id = str(uuid.uuid4())
        org_name = f"Test Org {i+1} - {fake.company()}"
        
        org = {
            "id": org_id,
            "name": org_name,
            "settings": {"test": True},
            "website": f"https://test-{i+1}.example.com",
            "domain": f"test-{i+1}.example.com",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        organizations.append(org)
        print(f"   Generated organization: {org_name} (ID: {org_id})")
        
        # Generate users for this organization
        for j in range(users_per_org):
            user_id = str(uuid.uuid4())
            role = "admin" if j == 0 else "member"
            
            # Create the organization-user relationship
            org_user = {
                "org_id": org_id,
                "user_id": user_id,
                "role": role,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            org_users.append(org_user)
            print(f"   Generated {role} user (ID: {user_id}) for org {org_name}")
    
    return {
        "organizations": organizations,
        "org_users": org_users
    }

def insert_test_data(data):
    """Insert test data into Supabase"""
    success_count = 0
    error_count = 0
    
    # Insert organizations
    print("\n🔄 Inserting organizations...")
    for org in data["organizations"]:
        try:
            response = supabase.table(Tables.ORGANIZATIONS).insert(org).execute()
            if response.data:
                print(f"   ✅ Inserted: {org['name']}")
                success_count += 1
            else:
                print(f"   ⚠️ No data returned for: {org['name']}")
                error_count += 1
        except Exception as e:
            print(f"   ❌ Error inserting {org['name']}: {str(e)}")
            error_count += 1
    
    # Insert organization-user relationships
    print("\n🔄 Inserting organization-user relationships...")
    for org_user in data["org_users"]:
        try:
            response = supabase.table(Tables.ORG_USERS).insert(org_user).execute()
            if response.data:
                print(f"   ✅ Inserted: User {org_user['user_id']} as {org_user['role']} in org {org_user['org_id']}")
                success_count += 1
            else:
                print(f"   ⚠️ No data returned for user {org_user['user_id']}")
                error_count += 1
        except Exception as e:
            print(f"   ❌ Error inserting user {org_user['user_id']}: {str(e)}")
            error_count += 1
    
    return {
        "success": success_count,
        "errors": error_count
    }

def verify_data_insertion():
    """Verify that data was inserted correctly"""
    print("\n🔍 Verifying data insertion...")
    
    try:
        # Check organizations
        org_response = supabase.table(Tables.ORGANIZATIONS).select("*").limit(10).execute()
        
        if hasattr(org_response, 'data') and org_response.data:
            org_count = len(org_response.data)
            print(f"   ✅ Found {org_count} organizations in the database")
            
            # Print some details for verification
            if org_count > 0:
                print("\n   📋 Sample organization data:")
                for i, org in enumerate(org_response.data[:2]):  # Show first 2 only
                    print(f"      {i+1}. {org.get('name')} (ID: {org.get('id')})")
        else:
            print("   ❌ No organizations found")
        
        # Check org users
        user_response = supabase.table(Tables.ORG_USERS).select("*").limit(10).execute()
        
        if hasattr(user_response, 'data') and user_response.data:
            user_count = len(user_response.data)
            print(f"   ✅ Found {user_count} organization-user relationships in the database")
            
            # Print some details for verification
            if user_count > 0:
                print("\n   📋 Sample org-user data:")
                for i, user in enumerate(user_response.data[:2]):  # Show first 2 only
                    print(f"      {i+1}. User ID: {user.get('user_id')} - Role: {user.get('role')} in Org: {user.get('org_id')}")
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
        response = supabase.from_('information_schema.tables').select('table_name').eq('table_schema', 'public').execute()
        
        if hasattr(response, 'data') and response.data:
            table_names = [table['table_name'] for table in response.data]
            print(f"   ✅ Found {len(table_names)} tables")
            print("   📋 Table names:")
            for i, name in enumerate(table_names):
                print(f"      {i+1}. {name}")
            
            # Check if our Tables class matches actual table names
            for table_name in [Tables.ORGANIZATIONS, Tables.ORG_USERS]:
                if table_name in table_names:
                    print(f"   ✅ Table '{table_name}' exists")
                else:
                    print(f"   ❌ Table '{table_name}' NOT FOUND!")
            
            return table_names
        else:
            print("   ❌ Could not retrieve table names")
            return []
    except Exception as e:
        print(f"   ❌ Error verifying table names: {str(e)}")
        return []

def main():
    print("🚀 Starting database insertion test...\n")

    # First, verify the exact table names to ensure we're using the right case
    table_names = verify_table_names()
    
    # Update table classes if needed based on verification
    if table_names:
        if Tables.ORGANIZATIONS not in table_names:
            potential_match = next((t for t in table_names if t.lower() == Tables.ORGANIZATIONS.lower()), None)
            if potential_match:
                print(f"   ⚠️ Updating ORGANIZATIONS table name to: {potential_match}")
                Tables.ORGANIZATIONS = potential_match
        
        if Tables.ORG_USERS not in table_names:
            potential_match = next((t for t in table_names if t.lower() == Tables.ORG_USERS.lower()), None)
            if potential_match:
                print(f"   ⚠️ Updating ORG_USERS table name to: {potential_match}")
                Tables.ORG_USERS = potential_match
    
    # Add permissive policies
    if not add_permissive_policies():
        print("\n❌ Could not add permissive policies. Would you like to continue anyway? (y/n)")
        choice = input().strip().lower()
        if choice != 'y':
            print("Exiting...")
            return
    
    # Generate test data
    test_data = generate_test_data(org_count=2, users_per_org=2)
    
    # Insert test data
    print("\n💾 Inserting test data...")
    results = insert_test_data(test_data)
    
    # Show summary
    print("\n📊 Test Results Summary:")
    print(f"   ✅ Successful insertions: {results['success']}")
    print(f"   ❌ Failed insertions: {results['errors']}")
    
    # Verify insertions
    verify_data_insertion()
    
    print("\n🏁 Test completed!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        print("\nTraceback:")
        traceback.print_exc()