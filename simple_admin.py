from app import app
from flask import render_template
from flask_login import login_required

@app.route('/admin-simple')
@login_required
def admin_simple():
    return render_template('simple_post.html', title='Admin Simple', content='Admin page is working!')
