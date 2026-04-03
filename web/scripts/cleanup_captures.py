import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from exts import db
from blueprints.models import Capture

def cleanup_captures(days=30):
    with app.app_context():
        limit_date = datetime.now() - timedelta(days=days)
        captures = Capture.query.filter(Capture.capture_time < limit_date).all()
        
        print(f"Found {len(captures)} captures older than {days} days.")
        
        for capture in captures:
            paths = [
                os.path.join(app.static_folder, capture.image_path),
                os.path.join(app.static_folder, capture.thumbnail_path) if capture.thumbnail_path else None
            ]
            
            for path in paths:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception as e:
                        print(f"Error deleting file {path}: {e}")
            
            db.session.delete(capture)
            
        db.session.commit()
        print("Cleanup completed.")

if __name__ == '__main__':
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    cleanup_captures(days)
