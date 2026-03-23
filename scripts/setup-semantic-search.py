#!/usr/bin/env python3
"""
Setup script for Friday Context Management semantic search capabilities
Installs required dependencies for embedding-based search
"""

import sys
import subprocess
import pkg_resources
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required for semantic search")
        print(f"Current version: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} is compatible")
    return True

def install_package(package):
    """Install a Python package using pip"""
    try:
        print(f"📦 Installing {package}...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", package
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print(f"✅ {package} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e.stderr.decode()}")
        return False

def check_package_installed(package):
    """Check if a package is already installed"""
    try:
        pkg_resources.get_distribution(package)
        return True
    except pkg_resources.DistributionNotFound:
        return False

def setup_semantic_dependencies():
    """Install dependencies for semantic search"""
    print("🔧 Setting up semantic search dependencies...")
    
    # Required packages for semantic search
    packages = [
        "sentence-transformers",
        "numpy",
        "PyYAML",
        "requests"
    ]
    
    installed_count = 0
    failed_packages = []
    
    for package in packages:
        if check_package_installed(package):
            print(f"✅ {package} already installed")
            installed_count += 1
        else:
            if install_package(package):
                installed_count += 1
            else:
                failed_packages.append(package)
    
    print(f"\n📊 Installation summary:")
    print(f"✅ Successfully installed: {installed_count}/{len(packages)}")
    
    if failed_packages:
        print(f"❌ Failed to install: {', '.join(failed_packages)}")
        print("\nAlternative installation methods:")
        print("1. Create a virtual environment:")
        print("   python -m venv context-venv")
        print("   source context-venv/bin/activate  # Linux/Mac")
        print("   context-venv\\Scripts\\activate     # Windows")
        print("   pip install sentence-transformers numpy PyYAML requests")
        print("\n2. Use conda:")
        print("   conda install -c conda-forge sentence-transformers numpy pyyaml requests")
        print("\n3. Install minimal dependencies and use text-only search")
        return False
    
    return True

def test_semantic_functionality():
    """Test if semantic search functionality works"""
    print("\n🧪 Testing semantic search functionality...")
    
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        print("📥 Downloading sentence transformer model (first time only)...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Test embedding generation
        test_texts = [
            "This is a test sentence for embeddings.",
            "Another example text for testing semantic similarity."
        ]
        
        embeddings = model.encode(test_texts)
        
        # Test similarity calculation
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        
        print(f"✅ Semantic search test successful!")
        print(f"   Model: all-MiniLM-L6-v2")
        print(f"   Embedding dimension: {embeddings.shape[1]}")
        print(f"   Test similarity: {similarity:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Semantic search test failed: {e}")
        print("Falling back to text-only search mode")
        return False

def create_requirements_file():
    """Create requirements.txt for semantic search dependencies"""
    project_root = Path(__file__).parent.parent
    requirements_file = project_root / "requirements-context.txt"
    
    requirements_content = """# Friday Context Management Dependencies
# Install with: pip install -r requirements-context.txt

# Core semantic search
sentence-transformers>=2.2.2
numpy>=1.21.0

# Configuration and data handling
PyYAML>=6.0
requests>=2.28.0

# Optional performance improvements
torch>=1.12.0  # For CUDA acceleration if available
scikit-learn>=1.1.0  # For additional similarity metrics

# Development dependencies (optional)
jupyter>=1.0.0  # For context analysis notebooks
matplotlib>=3.5.0  # For visualization
pandas>=1.4.0  # For data analysis
"""
    
    with open(requirements_file, 'w') as f:
        f.write(requirements_content)
    
    print(f"📄 Created {requirements_file}")
    print("   Install all dependencies with: pip install -r requirements-context.txt")

def setup_fallback_mode():
    """Setup fallback mode without semantic dependencies"""
    print("⚙️  Setting up fallback mode (text-only search)...")
    
    project_root = Path(__file__).parent.parent
    
    # Create simplified CLI without semantic dependencies
    simple_cli_content = '''#!/usr/bin/env python3
"""
Friday Context CLI - Lightweight version without semantic search
Falls back to text-based search when sentence-transformers is not available
"""

import sys
from pathlib import Path

# Add the enhanced CLI to path and run in text-only mode
PROJECT_ROOT = Path(__file__).parent.parent
enhanced_cli = PROJECT_ROOT / "bin" / "friday-ctx-enhanced"

if enhanced_cli.exists():
    import subprocess
    
    # Add --text-only flag if doing search
    args = sys.argv[1:]
    if len(args) > 0 and args[0] == "find" and "--text-only" not in args:
        args.append("--text-only")
    
    subprocess.run([str(enhanced_cli)] + args)
else:
    print("❌ Enhanced Friday Context CLI not found")
    print("Please ensure friday-ctx-enhanced exists in bin/")
'''
    
    fallback_cli = project_root / "bin" / "friday-ctx-simple"
    with open(fallback_cli, 'w') as f:
        f.write(simple_cli_content)
    
    fallback_cli.chmod(0o755)
    print(f"✅ Created fallback CLI at {fallback_cli}")

def main():
    """Main setup function"""
    print("🚀 Friday Context Management Semantic Search Setup")
    print("=" * 60)
    
    if not check_python_version():
        sys.exit(1)
    
    # Try to setup semantic dependencies
    semantic_success = setup_semantic_dependencies()
    
    if semantic_success:
        # Test semantic functionality
        test_success = test_semantic_functionality()
        
        if test_success:
            print("\n🎉 Semantic search setup complete!")
            print("\n📋 Usage:")
            print("   friday-ctx-enhanced find 'your query'      # Semantic search")
            print("   friday-ctx-enhanced find 'query' --text-only  # Text search")
            print("   friday-ctx-enhanced status                 # Check system status")
            print("   friday-ctx-enhanced index                  # Rebuild index")
        else:
            print("\n⚠️  Semantic dependencies installed but testing failed")
            print("   Text-only search will be used as fallback")
    else:
        print("\n⚠️  Could not install semantic dependencies")
        setup_fallback_mode()
    
    # Always create requirements file for reference
    create_requirements_file()
    
    print("\n📚 Next steps:")
    print("   1. Test the system: friday-ctx-enhanced find 'authentication'")
    print("   2. Build the index: friday-ctx-enhanced index")
    print("   3. Validate setup: ./scripts/validate-context.sh")
    print("\n🔗 For help:")
    print("   friday-ctx-enhanced --help")

if __name__ == "__main__":
    main()