#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timezone
from app import app, db, Post
import random

SAMPLE_POSTS = [
    {
        "title": "Gökyüzünde Bir Yıldız",
        "content": "<p>Gökyüzüne baktığımda, her zaman o parlak yıldızı görürdüm. Sanki bana bir şey anlatmak istiyordu, bir sır, belki de bir umut.</p><p>Yıllar geçti, ben büyüdüm, ama o yıldız hep oradaydı, beni izliyor, bana yol gösteriyordu.</p><p>Hayatın zorluklarında, en karanlık gecelerimde bile, o yıldız ışığıyla bana umut oldu.</p>",
        "category": "şiir",
        "author": "Ahmet Ümit"
    },
    {
        "title": "Eski Bir Anının İzinde",
        "content": "<p>Sokağın köşesindeki o eski bina, çocukluğumun en değerli anılarını saklıyordu. Her sabah okula giderken önünden geçerdim.</p><p>Şimdi yıllar sonra yeniden buradayım. Bina artık eskisi kadar büyük görünmüyor, ama içimde uyandırdığı duygular hâlâ aynı.</p><p>Bazı anılar zamana yenilmiyor, sadece bizimle birlikte olgunlaşıyor.</p>",
        "category": "öykü",
        "author": "Elif Şafak"
    },
    {
        "title": "Mavi Denizin Ardında",
        "content": "<p>Deniz, sonsuzluğun ve özgürlüğün simgesi. Mavi dalgaların ardında neler var acaba?</p><p>Belki de başka bir hayat, belki de sadece daha fazla dalga...</p><p>Kumsalda otururken, dalgaların sesiyle kendimi kaybediyorum. Sanki deniz beni çağırıyor, uzaklara götürmek istiyor.</p>",
        "category": "deneme",
        "author": "Orhan Pamuk"
    },
    {
        "title": "Akşam Güneşi",
        "content": "<p>Akşam güneşi, dağların ardından son ışıklarını saçıyordu. Kızıl bir ışık, tüm şehri kaplamıştı.</p><p>Pencere kenarında oturan yaşlı adam, her zamanki gibi bu manzarayı izliyordu. Yılların yorgunluğunu taşıyan gözlerinde, bir zamanlar yaşadığı mutlulukların izleri vardı.</p>",
        "category": "öykü",
        "author": "Sabahattin Ali"
    },
    {
        "title": "Rüzgârın Söyledikleri",
        "content": "<p>Rüzgâr estiğinde, kulak verin. Size neler anlatıyor?</p><p>Uzak diyarlardan gelen haberler mi, yoksa yakındaki bir sırrın fısıltıları mı?</p><p>Rüzgârın dilini anlamak, belki de en eski bilgeliktir.</p>",
        "category": "şiir",
        "author": "Nazım Hikmet"
    }
]

def main():
    print("=" * 50)
    print("ADDING SAMPLE POSTS TO DATABASE")
    print("=" * 50)
    
    # Check for images
    upload_dir = app.config['UPLOAD_FOLDER']
    available_images = []
    
    if os.path.exists(upload_dir):
        available_images = [f for f in os.listdir(upload_dir) 
                           if os.path.isfile(os.path.join(upload_dir, f)) and 
                           not f.startswith('.')]
    
    print(f"Found {len(available_images)} images to use")
    
    with app.app_context():
        # First check if we already have posts
        existing_post_count = Post.query.count()
        print(f"Current post count: {existing_post_count}")
        
        # Add sample posts
        print("\nAdding sample posts...")
        
        for i, post_data in enumerate(SAMPLE_POSTS):
            # Skip if we already have this post (by title)
            if Post.query.filter_by(title=post_data["title"]).first():
                print(f"Post '{post_data['title']}' already exists, skipping...")
                continue
                
            new_post = Post(
                title=post_data["title"],
                content=post_data["content"],
                category=post_data["category"],
                author=post_data["author"],
                created_at=datetime.now(timezone.utc)
            )
            
            # Assign a random image if available
            if available_images:
                img_index = i % len(available_images)
                image_filename = available_images[img_index]
                new_post.image_url = image_filename
                print(f"Adding post '{new_post.title}' with image '{image_filename}'")
            else:
                print(f"Adding post '{new_post.title}' without image")
                
            db.session.add(new_post)
            
        # Commit to database
        db.session.commit()
        
        # Verify
        new_post_count = Post.query.count()
        print(f"\nAdded {new_post_count - existing_post_count} new posts")
        print(f"Total posts in database: {new_post_count}")
        
        # List the posts
        if new_post_count > 0:
            posts = Post.query.order_by(Post.created_at.desc()).all()
            print("\nPosts in database:")
            for i, post in enumerate(posts):
                created_at = post.created_at.strftime("%Y-%m-%d %H:%M:%S") if post.created_at else "None"
                print(f"{i+1}. ID: {post.id}, Title: {post.title}")
                print(f"   Category: {post.category}, Author: {post.author}")
                print(f"   Image: {'Yes - ' + post.image_url if post.image_url else 'No'}")

if __name__ == "__main__":
    main() 