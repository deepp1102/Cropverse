"""
Seed Firestore Database with Initial Settings
Populates the settings collection with default threshold values
"""

import os
import sys
from datetime import datetime

# Add functions directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'functions'))

import firebase_admin
from firebase_admin import credentials, firestore

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        # Check if already initialized
        firebase_admin.get_app()
        print("✅ Firebase already initialized")
    except ValueError:
        # Initialize with credentials
        cred_path = os.path.join(os.path.dirname(__file__), '..', 'functions', 'serviceAccountKey.json')
        
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized with service account key")
        else:
            # Try using application default credentials
            firebase_admin.initialize_app()
            print("✅ Firebase initialized with default credentials")
    
    return firestore.client()

def seed_settings(db):
    """Seed the settings collection with default values"""
    
    settings_data = {
        # Temperature thresholds (°C)
        'temp_max': {
            'value': 35,
            'description': 'Maximum critical temperature threshold',
            'unit': '°C'
        },
        'temp_min': {
            'value': 10,
            'description': 'Minimum critical temperature threshold',
            'unit': '°C'
        },
        'temp_warning_max': {
            'value': 32,
            'description': 'Maximum warning temperature threshold',
            'unit': '°C'
        },
        'temp_warning_min': {
            'value': 15,
            'description': 'Minimum warning temperature threshold',
            'unit': '°C'
        },
        
        # Humidity thresholds (%)
        'humidity_max': {
            'value': 85,
            'description': 'Maximum critical humidity threshold',
            'unit': '%'
        },
        'humidity_min': {
            'value': 40,
            'description': 'Minimum critical humidity threshold',
            'unit': '%'
        },
        'humidity_warning_max': {
            'value': 80,
            'description': 'Maximum warning humidity threshold',
            'unit': '%'
        },
        'humidity_warning_min': {
            'value': 45,
            'description': 'Minimum warning humidity threshold',
            'unit': '%'
        },
        
        # Methane thresholds (PPM)
        'methane_critical': {
            'value': 300,
            'description': 'Critical methane level - activate exhaust fan',
            'unit': 'PPM'
        },
        'methane_warning': {
            'value': 200,
            'description': 'Warning methane level',
            'unit': 'PPM'
        },
        
        # Other gases thresholds (PPM)
        'other_gases_critical': {
            'value': 500,
            'description': 'Critical other gases level',
            'unit': 'PPM'
        },
        'other_gases_warning': {
            'value': 400,
            'description': 'Warning other gases level',
            'unit': 'PPM'
        },
        
        # System settings
        'exhaust_fan_auto': {
            'value': True,
            'description': 'Automatically control exhaust fan based on thresholds',
            'unit': 'boolean'
        },
        'alert_cooldown_minutes': {
            'value': 15,
            'description': 'Minimum time between duplicate alerts',
            'unit': 'minutes'
        }
    }
    
    settings_ref = db.collection('settings')
    
    print("\n" + "="*60)
    print("🌱 Seeding Firestore Settings Collection")
    print("="*60)
    
    created_count = 0
    updated_count = 0
    
    for setting_key, setting_data in settings_data.items():
        try:
            doc_ref = settings_ref.document(setting_key)
            doc = doc_ref.get()
            
            # Add metadata
            setting_data['updated_at'] = datetime.utcnow()
            
            if doc.exists:
                # Update existing
                doc_ref.update(setting_data)
                print(f"🔄 Updated: {setting_key} = {setting_data['value']} {setting_data['unit']}")
                updated_count += 1
            else:
                # Create new
                setting_data['created_at'] = datetime.utcnow()
                doc_ref.set(setting_data)
                print(f"✅ Created: {setting_key} = {setting_data['value']} {setting_data['unit']}")
                created_count += 1
                
        except Exception as e:
            print(f"❌ Error seeding {setting_key}: {str(e)}")
    
    print("\n" + "="*60)
    print(f"✅ Seeding Complete!")
    print(f"📊 Created: {created_count} settings")
    print(f"📊 Updated: {updated_count} settings")
    print(f"📊 Total: {created_count + updated_count} settings")
    print("="*60 + "\n")

def verify_settings(db):
    """Verify all settings were created correctly"""
    
    print("\n" + "="*60)
    print("🔍 Verifying Settings in Firestore")
    print("="*60)
    
    settings_ref = db.collection('settings')
    docs = settings_ref.stream()
    
    settings_count = 0
    for doc in docs:
        data = doc.to_dict()
        print(f"✅ {doc.id}: {data.get('value')} {data.get('unit', '')} - {data.get('description', 'N/A')}")
        settings_count += 1
    
    if settings_count == 0:
        print("❌ No settings found!")
    else:
        print(f"\n📊 Total settings verified: {settings_count}")
    
    print("="*60 + "\n")

def main():
    """Main execution function"""
    
    print("\n" + "="*60)
    print("🌱 CropVerse Firestore Seeding Script")
    print("="*60 + "\n")
    
    try:
        # Initialize Firebase
        db = initialize_firebase()
        
        # Seed settings
        seed_settings(db)
        
        # Verify settings
        verify_settings(db)
        
        print("✅ Firestore seeding completed successfully!\n")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()