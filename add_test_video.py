from app import app, db, Video
from datetime import datetime, UTC

with app.app_context():
    # Check if any videos exist
    video_count = Video.query.count()
    print(f"Current video count: {video_count}")
    
    # Add a sample YouTube video if none exist
    if video_count == 0:
        test_video = Video(
            title="Test Video",
            youtube_embed="dQw4w9WgXcQ",  # Rick Astley - Never Gonna Give You Up
            created_at=datetime.now(UTC)
        )
        db.session.add(test_video)
        db.session.commit()
        print("Added test video successfully!")
    else:
        print("Videos already exist, no test video added.") 