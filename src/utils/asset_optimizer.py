import os
import json
import hashlib
import gzip
import shutil
from PIL import Image
import csscompressor
import jsmin
from typing import List, Dict, Any

class AssetOptimizer:
    def __init__(self, static_dir: str = "static", output_dir: str = "optimized"):
        """Initialize asset optimizer"""
        self.static_dir = static_dir
        self.output_dir = output_dir
        self.manifest = {}
        self.stats = {
            'original_size': 0,
            'optimized_size': 0,
            'files_processed': 0
        }
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
    def optimize_images(self, quality: int = 85, max_size: tuple = (1920, 1080)) -> Dict[str, Any]:
        """Optimize images in static directory"""
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        optimized_images = {}
        
        for root, dirs, files in os.walk(self.static_dir):
            for file in files:
                if file.lower().endswith(image_extensions):
                    input_path = os.path.join(root, file)
                    relative_path = os.path.relpath(input_path, self.static_dir)
                    output_path = os.path.join(self.output_dir, relative_path)
                    
                    # Create output directory if needed
                    output_dir = os.path.dirname(output_path)
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                        
                    try:
                        # Open and optimize image
                        with Image.open(input_path) as img:
                            # Resize if larger than max_size
                            if img.width > max_size[0] or img.height > max_size[1]:
                                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                            
                            # Save optimized image
                            if file.lower().endswith(('.jpg', '.jpeg')):
                                img.save(output_path, 'JPEG', quality=quality, optimize=True)
                            elif file.lower().endswith('.png'):
                                img.save(output_path, 'PNG', optimize=True)
                            elif file.lower().endswith('.webp'):
                                img.save(output_path, 'WEBP', quality=quality, method=6)
                            else:
                                img.save(output_path, optimize=True)
                                
                        # Calculate size savings
                        original_size = os.path.getsize(input_path)
                        optimized_size = os.path.getsize(output_path)
                        savings = original_size - optimized_size
                        savings_percent = (savings / original_size * 100) if original_size > 0 else 0
                        
                        optimized_images[relative_path] = {
                            'original_size': original_size,
                            'optimized_size': optimized_size,
                            'savings': savings,
                            'savings_percent': round(savings_percent, 2)
                        }
                        
                        # Update manifest
                        self.manifest[relative_path] = self._generate_file_hash(output_path)
                        self.stats['original_size'] += original_size
                        self.stats['optimized_size'] += optimized_size
                        self.stats['files_processed'] += 1
                        
                    except Exception as e:
                        print(f"Error optimizing image {file}: {e}")
                        
        return optimized_images
        
    def minify_css(self) -> Dict[str, Any]:
        """Minify CSS files"""
        minified_css = {}
        
        for root, dirs, files in os.walk(self.static_dir):
            for file in files:
                if file.endswith('.css'):
                    input_path = os.path.join(root, file)
                    relative_path = os.path.relpath(input_path, self.static_dir)
                    output_path = os.path.join(self.output_dir, relative_path)
                    
                    # Create output directory if needed
                    output_dir = os.path.dirname(output_path)
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                        
                    try:
                        # Read and minify CSS
                        with open(input_path, 'r', encoding='utf-8') as f:
                            css_content = f.read()
                            
                        minified_content = csscompressor.compress(css_content)
                        
                        # Write minified CSS
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(minified_content)
                            
                        # Calculate size savings
                        original_size = len(css_content.encode('utf-8'))
                        optimized_size = len(minified_content.encode('utf-8'))
                        savings = original_size - optimized_size
                        savings_percent = (savings / original_size * 100) if original_size > 0 else 0
                        
                        minified_css[relative_path] = {
                            'original_size': original_size,
                            'optimized_size': optimized_size,
                            'savings': savings,
                            'savings_percent': round(savings_percent, 2)
                        }
                        
                        # Update manifest
                        self.manifest[relative_path] = self._generate_file_hash(output_path)
                        self.stats['original_size'] += original_size
                        self.stats['optimized_size'] += optimized_size
                        self.stats['files_processed'] += 1
                        
                    except Exception as e:
                        print(f"Error minifying CSS {file}: {e}")
                        
        return minified_css
        
    def minify_js(self) -> Dict[str, Any]:
        """Minify JavaScript files"""
        minified_js = {}
        
        for root, dirs, files in os.walk(self.static_dir):
            for file in files:
                if file.endswith('.js') and not file.endswith('.min.js'):
                    input_path = os.path.join(root, file)
                    relative_path = os.path.relpath(input_path, self.static_dir)
                    output_filename = file.replace('.js', '.min.js')
                    output_path = os.path.join(self.output_dir, os.path.dirname(relative_path), output_filename)
                    
                    # Create output directory if needed
                    output_dir = os.path.dirname(output_path)
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                        
                    try:
                        # Read and minify JavaScript
                        with open(input_path, 'r', encoding='utf-8') as f:
                            js_content = f.read()
                            
                        minified_content = jsmin.jsmin(js_content)
                        
                        # Write minified JavaScript
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(minified_content)
                            
                        # Calculate size savings
                        original_size = len(js_content.encode('utf-8'))
                        optimized_size = len(minified_content.encode('utf-8'))
                        savings = original_size - optimized_size
                        savings_percent = (savings / original_size * 100) if original_size > 0 else 0
                        
                        output_relative_path = os.path.join(os.path.dirname(relative_path), output_filename)
                        minified_js[output_relative_path] = {
                            'original_size': original_size,
                            'optimized_size': optimized_size,
                            'savings': savings,
                            'savings_percent': round(savings_percent, 2)
                        }
                        
                        # Update manifest
                        self.manifest[output_relative_path] = self._generate_file_hash(output_path)
                        self.stats['original_size'] += original_size
                        self.stats['optimized_size'] += optimized_size
                        self.stats['files_processed'] += 1
                        
                    except Exception as e:
                        print(f"Error minifying JavaScript {file}: {e}")
                        
        return minified_js
        
    def compress_files(self, compression_level: int = 9) -> Dict[str, Any]:
        """Compress files with gzip"""
        compressed_files = {}
        
        for root, dirs, files in os.walk(self.output_dir):
            for file in files:
                # Skip already compressed files
                if file.endswith(('.gz', '.zip', '.7z')):
                    continue
                    
                input_path = os.path.join(root, file)
                relative_path = os.path.relpath(input_path, self.output_dir)
                output_path = input_path + '.gz'
                
                try:
                    # Compress file with gzip
                    with open(input_path, 'rb') as f_in:
                        with gzip.open(output_path, 'wb', compresslevel=compression_level) as f_out:
                            shutil.copyfileobj(f_in, f_out)
                            
                    # Calculate size savings
                    original_size = os.path.getsize(input_path)
                    compressed_size = os.path.getsize(output_path)
                    savings = original_size - compressed_size
                    savings_percent = (savings / original_size * 100) if original_size > 0 else 0
                    
                    compressed_files[relative_path] = {
                        'original_size': original_size,
                        'compressed_size': compressed_size,
                        'savings': savings,
                        'savings_percent': round(savings_percent, 2)
                    }
                    
                    # Update manifest for compressed version
                    compressed_relative_path = relative_path + '.gz'
                    self.manifest[compressed_relative_path] = self._generate_file_hash(output_path)
                    
                except Exception as e:
                    print(f"Error compressing file {file}: {e}")
                    
        return compressed_files
        
    def generate_manifest(self, manifest_file: str = "asset-manifest.json"):
        """Generate asset manifest file"""
        manifest_path = os.path.join(self.output_dir, manifest_file)
        
        try:
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(self.manifest, f, indent=2)
            print(f"Asset manifest generated: {manifest_path}")
        except Exception as e:
            print(f"Error generating manifest: {e}")
            
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        total_savings = self.stats['original_size'] - self.stats['optimized_size']
        savings_percent = (total_savings / self.stats['original_size'] * 100) if self.stats['original_size'] > 0 else 0
        
        return {
            'files_processed': self.stats['files_processed'],
            'original_size_bytes': self.stats['original_size'],
            'optimized_size_bytes': self.stats['optimized_size'],
            'total_savings_bytes': total_savings,
            'savings_percentage': round(savings_percent, 2),
            'original_size_human': self._format_bytes(self.stats['original_size']),
            'optimized_size_human': self._format_bytes(self.stats['optimized_size']),
            'total_savings_human': self._format_bytes(total_savings)
        }
        
    def _generate_file_hash(self, file_path: str) -> str:
        """Generate SHA256 hash of file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            print(f"Error generating hash for {file_path}: {e}")
            return ""
            
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} TB"
        
    def clean_output_directory(self):
        """Clean output directory"""
        try:
            if os.path.exists(self.output_dir):
                shutil.rmtree(self.output_dir)
                os.makedirs(self.output_dir)
            self.manifest = {}
            self.stats = {
                'original_size': 0,
                'optimized_size': 0,
                'files_processed': 0
            }
            print(f"Output directory cleaned: {self.output_dir}")
        except Exception as e:
            print(f"Error cleaning output directory: {e}")

# Example usage
if __name__ == "__main__":
    # Initialize asset optimizer
    optimizer = AssetOptimizer("static", "optimized")
    
    # Clean output directory
    optimizer.clean_output_directory()
    
    # Optimize images
    print("Optimizing images...")
    image_results = optimizer.optimize_images()
    print(f"Optimized {len(image_results)} images")
    
    # Minify CSS
    print("Minifying CSS...")
    css_results = optimizer.minify_css()
    print(f"Minified {len(css_results)} CSS files")
    
    # Minify JavaScript
    print("Minifying JavaScript...")
    js_results = optimizer.minify_js()
    print(f"Minified {len(js_results)} JavaScript files")
    
    # Compress files
    print("Compressing files...")
    compression_results = optimizer.compress_files()
    print(f"Compressed {len(compression_results)} files")
    
    # Generate manifest
    optimizer.generate_manifest()
    
    # Print statistics
    stats = optimizer.get_optimization_stats()
    print("\nOptimization Statistics:")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Original size: {stats['original_size_human']}")
    print(f"Optimized size: {stats['optimized_size_human']}")
    print(f"Total savings: {stats['total_savings_human']} ({stats['savings_percentage']}%)")