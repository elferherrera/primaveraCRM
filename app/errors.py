from flask import render_template
from app import app
from flask_login import login_required


@app.errorhandler(404)
@login_required
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
@login_required
def internal_server_error(e):
    return render_template('500.html'), 500
