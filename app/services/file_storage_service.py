"""Service for storing generated files (HTML charts, tables, etc.)."""

import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from ..utils.file_utils import ensure_directory_exists


class FileStorageService:
    """Service for storing and managing generated files."""
    
    def __init__(self):
        self.storage_dir = "generated_files"
        self.charts_dir = os.path.join(self.storage_dir, "charts")
        self.tables_dir = os.path.join(self.storage_dir, "tables")
        
        # Ensure directories exist
        ensure_directory_exists(self.storage_dir)
        ensure_directory_exists(self.charts_dir)
        ensure_directory_exists(self.tables_dir)
        
        print(f"📁 FileStorageService initialized with storage directory: {self.storage_dir}")
    
    def store_chart_html(self, session_id: str, html_content: str, chart_title: str = "chart") -> Dict[str, str]:
        """Store chart HTML and return file info."""
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{session_id}_{chart_title}_{timestamp}.html"
            filepath = os.path.join(self.charts_dir, filename)
            
            # Write HTML content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            file_info = {
                "type": "chart_html",
                "filename": filename,
                "filepath": filepath,
                "session_id": session_id,
                "title": chart_title,
                "size_bytes": len(html_content.encode('utf-8')),
                "created_at": datetime.now().isoformat(),
                "url": f"/generated_files/charts/{filename}"
            }
            
            print(f"📊 Chart HTML stored: {filename} ({file_info['size_bytes']} bytes)")
            return file_info
            
        except Exception as e:
            print(f"❌ Error storing chart HTML: {e}")
            return {}
    
    def store_table_data(self, session_id: str, table_content: str, table_title: str = "table") -> Dict[str, str]:
        """Store table data and return file info."""
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{session_id}_{table_title}_{timestamp}.txt"
            filepath = os.path.join(self.tables_dir, filename)
            
            # Write table content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(table_content)
            
            file_info = {
                "type": "table_data",
                "filename": filename,
                "filepath": filepath,
                "session_id": session_id,
                "title": table_title,
                "size_bytes": len(table_content.encode('utf-8')),
                "created_at": datetime.now().isoformat(),
                "url": f"/generated_files/tables/{filename}"
            }
            
            print(f"📋 Table data stored: {filename} ({file_info['size_bytes']} bytes)")
            return file_info
            
        except Exception as e:
            print(f"❌ Error storing table data: {e}")
            return {}
    
    def get_session_files(self, session_id: str) -> List[Dict[str, str]]:
        """Get all files for a specific session."""
        files = []
        
        try:
            # Check charts directory
            for filename in os.listdir(self.charts_dir):
                if filename.startswith(session_id):
                    filepath = os.path.join(self.charts_dir, filename)
                    stat = os.stat(filepath)
                    files.append({
                        "type": "chart_html",
                        "filename": filename,
                        "filepath": filepath,
                        "size_bytes": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "url": f"/generated_files/charts/{filename}"
                    })
            
            # Check tables directory
            for filename in os.listdir(self.tables_dir):
                if filename.startswith(session_id):
                    filepath = os.path.join(self.tables_dir, filename)
                    stat = os.stat(filepath)
                    files.append({
                        "type": "table_data",
                        "filename": filename,
                        "filepath": filepath,
                        "size_bytes": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "url": f"/generated_files/tables/{filename}"
                    })
            
            return sorted(files, key=lambda x: x["created_at"], reverse=True)
            
        except Exception as e:
            print(f"❌ Error getting session files: {e}")
            return []
    
    def cleanup_session_files(self, session_id: str) -> int:
        """Clean up all files for a session."""
        deleted_count = 0
        
        try:
            # Clean up charts
            for filename in os.listdir(self.charts_dir):
                if filename.startswith(session_id):
                    filepath = os.path.join(self.charts_dir, filename)
                    os.remove(filepath)
                    deleted_count += 1
            
            # Clean up tables
            for filename in os.listdir(self.tables_dir):
                if filename.startswith(session_id):
                    filepath = os.path.join(self.tables_dir, filename)
                    os.remove(filepath)
                    deleted_count += 1
            
            if deleted_count > 0:
                print(f"🗑️ Cleaned up {deleted_count} files for session: {session_id}")
            
            return deleted_count
            
        except Exception as e:
            print(f"❌ Error cleaning up session files: {e}")
            return 0
    
    def get_file_content(self, filepath: str) -> Optional[str]:
        """Get content of a stored file."""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            return None
        except Exception as e:
            print(f"❌ Error reading file {filepath}: {e}")
            return None


# Global file storage service instance
file_storage_service = FileStorageService()


def get_file_storage_service() -> FileStorageService:
    """Get the global file storage service instance."""
    return file_storage_service
