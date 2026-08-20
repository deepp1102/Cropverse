"""
Backend Endpoint Analyzer
Discovers all routes, their methods, parameters, and generates frontend integration guide
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory and functions directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'functions'))

# Mock Firebase before importing main
os.environ['FIREBASE_SKIP_INIT'] = 'true'

def analyze_backend():
    """Analyze Flask backend and generate comprehensive endpoint report"""
    
    print("\n" + "="*80)
    print("🔍 CropVerse Backend Endpoint Analysis")
    print("="*80 + "\n")
    
    try:
        # Suppress Firebase initialization
        import firebase_admin
        from unittest.mock import MagicMock
        
        # Mock the firestore client before importing main
        sys.modules['firebase_admin.firestore'] = MagicMock()
        
        from main import flask_app
        
        endpoints = []
        
        # Iterate through all registered routes
        for rule in flask_app.url_map.iter_rules():
            # Skip static file routes
            if rule.endpoint == 'static':
                continue
            
            # Get HTTP methods (excluding HEAD and OPTIONS)
            methods = sorted(list(rule.methods - {'HEAD', 'OPTIONS'}))
            
            # Get function documentation
            view_func = flask_app.view_functions.get(rule.endpoint)
            docstring = view_func.__doc__ if view_func and view_func.__doc__ else "No description available"
            
            # Extract parameters from route
            params = list(rule.arguments) if hasattr(rule, 'arguments') else []
            
            endpoint_info = {
                'path': str(rule),
                'methods': methods,
                'endpoint': rule.endpoint,
                'description': docstring.strip(),
                'params': params,
                'blueprint': rule.endpoint.split('.')[0] if '.' in rule.endpoint else 'main'
            }
            
            endpoints.append(endpoint_info)
        
        # Sort endpoints by path
        endpoints.sort(key=lambda x: x['path'])
        
        # Generate report
        generate_console_report(endpoints)
        generate_json_report(endpoints)
        generate_markdown_report(endpoints)
        generate_frontend_guide(endpoints)
        
        return endpoints
        
    except Exception as e:
        print(f"❌ Error analyzing backend: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def generate_console_report(endpoints):
    """Print formatted report to console"""
    
    print("\n" + "="*80)
    print("📊 ENDPOINT INVENTORY")
    print("="*80 + "\n")
    
    # Group by blueprint
    blueprints = {}
    for ep in endpoints:
        bp = ep['blueprint']
        if bp not in blueprints:
            blueprints[bp] = []
        blueprints[bp].append(ep)
    
    total_endpoints = len(endpoints)
    
    for blueprint, eps in sorted(blueprints.items()):
        print(f"\n{'─'*80}")
        print(f"📦 {blueprint.upper()} Blueprint ({len(eps)} endpoints)")
        print(f"{'─'*80}\n")
        
        for ep in eps:
            methods_str = ', '.join(ep['methods'])
            print(f"  {methods_str:8} {ep['path']}")
            
            # Print first line of description
            desc_lines = ep['description'].split('\n')
            if desc_lines and desc_lines[0].strip():
                print(f"           ↳ {desc_lines[0].strip()}")
            
            # Print query parameters if mentioned in description
            if 'Query parameters' in ep['description'] or 'parameters:' in ep['description'].lower():
                print(f"           ↳ 📝 Has query parameters")
            
            print()
    
    print(f"{'='*80}")
    print(f"✅ Total Endpoints: {total_endpoints}")
    print(f"{'='*80}\n")


def generate_json_report(endpoints):
    """Generate JSON report file"""
    
    output_file = 'backend_endpoints.json'
    
    report = {
        'generated_at': datetime.now().isoformat(),
        'total_endpoints': len(endpoints),
        'endpoints': endpoints
    }
    
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ JSON report saved: {output_file}\n")


def generate_markdown_report(endpoints):
    """Generate Markdown documentation"""
    
    output_file = 'BACKEND_API_DOCS.md'
    
    with open(output_file, 'w') as f:
        f.write("# CropVerse Backend API Documentation\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Total Endpoints:** {len(endpoints)}\n\n")
        f.write("---\n\n")
        
        # Group by blueprint
        blueprints = {}
        for ep in endpoints:
            bp = ep['blueprint']
            if bp not in blueprints:
                blueprints[bp] = []
            blueprints[bp].append(ep)
        
        # Table of contents
        f.write("## Table of Contents\n\n")
        for blueprint in sorted(blueprints.keys()):
            f.write(f"- [{blueprint.upper()}](#{blueprint.lower()})\n")
        f.write("\n---\n\n")
        
        # Detailed documentation for each blueprint
        for blueprint, eps in sorted(blueprints.items()):
            f.write(f"## {blueprint.upper()}\n\n")
            
            for ep in eps:
                methods_str = ' | '.join(ep['methods'])
                f.write(f"### `{methods_str}` {ep['path']}\n\n")
                f.write(f"**Description:**\n```\n{ep['description']}\n```\n\n")
                
                if ep['params']:
                    f.write(f"**Path Parameters:** {', '.join(ep['params'])}\n\n")
                
                # Example curl command
                method = ep['methods'][0]
                if method == 'GET':
                    f.write(f"**Example:**\n```bash\n")
                    f.write(f"curl http://localhost:8080{ep['path']}\n")
                    f.write(f"```\n\n")
                elif method == 'POST':
                    f.write(f"**Example:**\n```bash\n")
                    f.write(f"curl -X POST http://localhost:8080{ep['path']} \\\n")
                    f.write(f"  -H 'Content-Type: application/json' \\\n")
                    f.write(f"  -d '{{\"key\": \"value\"}}'\n")
                    f.write(f"```\n\n")
                
                f.write("---\n\n")
    
    print(f"✅ Markdown docs saved: {output_file}\n")


def generate_frontend_guide(endpoints):
    """Generate frontend integration guide"""
    
    output_file = 'FRONTEND_INTEGRATION_GUIDE.md'
    
    # Categorize endpoints by frontend feature
    features = {
        'Dashboard': [],
        'Analytics': [],
        'Alerts/Notifications': [],
        'Settings': [],
        'Chatbot': [],
        'Arduino': [],
        'Authentication': [],
        'Other': []
    }
    
    for ep in endpoints:
        path = ep['path'].lower()
        
        if 'dashboard' in path:
            features['Dashboard'].append(ep)
        elif 'analytics' in path or 'trends' in path:
            features['Analytics'].append(ep)
        elif 'alert' in path or 'notification' in path:
            features['Alerts/Notifications'].append(ep)
        elif 'setting' in path:
            features['Settings'].append(ep)
        elif 'chatbot' in path or 'ai' in path:
            features['Chatbot'].append(ep)
        elif 'arduino' in path:
            features['Arduino'].append(ep)
        elif 'auth' in path or 'login' in path:
            features['Authentication'].append(ep)
        else:
            features['Other'].append(ep)
    
    with open(output_file, 'w') as f:
        f.write("# Frontend Integration Guide\n\n")
        f.write("## Missing Frontend Features\n\n")
        f.write("Based on available backend endpoints, here are features you can add to your frontend:\n\n")
        
        for feature_name, feature_endpoints in features.items():
            if not feature_endpoints:
                continue
            
            f.write(f"### {feature_name}\n\n")
            f.write(f"**Available Endpoints:** {len(feature_endpoints)}\n\n")
            
            for ep in feature_endpoints:
                methods_str = ' | '.join(ep['methods'])
                f.write(f"#### `{methods_str}` {ep['path']}\n\n")
                
                # Suggest frontend implementation
                if 'GET' in ep['methods']:
                    f.write("**Frontend Usage:**\n```javascript\n")
                    endpoint_name = ep['path'].split('/')[-1].replace('-', '_')
                    f.write(f"// Fetch data\n")
                    f.write(f"const response = await api.request('{ep['path']}');\n")
                    f.write(f"console.log(response.data);\n")
                    f.write("```\n\n")
                
                # Check if implemented
                f.write("**Current Status:**\n")
                if any(keyword in ep['path'].lower() for keyword in ['summary', 'latest-readings', 'alerts', 'trends']):
                    f.write("- ✅ Implemented in dashboard.js\n\n")
                else:
                    f.write("- ❌ NOT implemented yet\n")
                    f.write("- 💡 **Suggestion:** Add this feature to enhance user experience\n\n")
                
                f.write("---\n\n")
        
        # Add recommendations
        f.write("\n## 🎯 Recommended Frontend Additions\n\n")
        
        recommendations = [
            {
                'feature': 'Settings Management UI',
                'priority': 'HIGH',
                'description': 'Add a settings page where admins can adjust temperature/humidity thresholds',
                'endpoints': ['GET /api/settings', 'PUT /api/settings/{key}']
            },
            {
                'feature': 'Alert Management',
                'priority': 'MEDIUM',
                'description': 'Add ability to mark alerts as resolved, filter by type, and view alert history',
                'endpoints': ['GET /api/dashboard/alerts', 'PUT /api/alerts/{id}/resolve']
            },
            {
                'feature': 'Export/Reports',
                'priority': 'MEDIUM',
                'description': 'Add buttons to download sensor data as CSV or generate PDF reports',
                'endpoints': ['GET /api/reports/csv', 'GET /api/reports/pdf']
            },
            {
                'feature': 'User Authentication UI',
                'priority': 'LOW',
                'description': 'Add login/register pages if authentication endpoints exist',
                'endpoints': ['POST /api/auth/login', 'POST /api/auth/register']
            }
        ]
        
        for rec in recommendations:
            f.write(f"### {rec['priority']}: {rec['feature']}\n\n")
            f.write(f"**Description:** {rec['description']}\n\n")
            f.write(f"**Required Endpoints:**\n")
            for endpoint in rec['endpoints']:
                f.write(f"- `{endpoint}`\n")
            f.write("\n")
    
    print(f"✅ Frontend guide saved: {output_file}\n")


def generate_comparison_report(endpoints):
    """Compare backend endpoints with frontend implementation"""
    
    print("\n" + "="*80)
    print("📊 BACKEND vs FRONTEND COMPARISON")
    print("="*80 + "\n")
    
    # Frontend implemented endpoints (from your current code)
    frontend_implemented = [
        '/api/dashboard/summary',
        '/api/dashboard/latest-readings',
        '/api/dashboard/alerts',
        '/api/analytics/trends',
        '/api/chatbot/message',
    ]
    
    print("✅ IMPLEMENTED IN FRONTEND:\n")
    for path in frontend_implemented:
        matching = [ep for ep in endpoints if ep['path'] == path]
        if matching:
            print(f"  ✓ {path}")
    
    print("\n❌ NOT IMPLEMENTED IN FRONTEND:\n")
    missing = [ep for ep in endpoints if ep['path'] not in frontend_implemented and ep['blueprint'] != 'main']
    
    for ep in missing:
        methods = ', '.join(ep['methods'])
        print(f"  ✗ {methods:8} {ep['path']}")
    
    print(f"\n{'='*80}")
    print(f"📈 Implementation Status:")
    print(f"   Implemented: {len(frontend_implemented)} endpoints")
    print(f"   Available: {len(endpoints)} endpoints")
    print(f"   Missing: {len(missing)} endpoints")
    print(f"   Coverage: {len(frontend_implemented)/len(endpoints)*100:.1f}%")
    print(f"{'='*80}\n")


def main():
    """Main execution"""
    
    # Check if running from correct directory
    if not os.path.exists('functions/main.py'):
        print("❌ Error: Must run from project root directory")
        print("   cd C:\\Users\\atharv\\Desktop\\SIH_2025\\cropverse-firebase")
        return
    
    # Analyze backend
    endpoints = analyze_backend()
    
    if endpoints:
        # Generate comparison
        generate_comparison_report(endpoints)
        
        print("\n" + "="*80)
        print("✅ Analysis Complete!")
        print("="*80)
        print("\nGenerated files:")
        print("  📄 backend_endpoints.json - Machine-readable endpoint list")
        print("  📄 BACKEND_API_DOCS.md - Complete API documentation")
        print("  📄 FRONTEND_INTEGRATION_GUIDE.md - Frontend implementation guide")
        print("\n")


if __name__ == '__main__':
    main()