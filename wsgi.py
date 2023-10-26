from app import create_app, db, admin
from dotenv import load_dotenv
from flask import render_template
from flask_admin.contrib.sqla import ModelView
from app.main.models import Announcement
import arrow


load_dotenv()

app = create_app()

from app.auth.models import *
admin.add_view(ModelView(User, db.session, category='Users'))

from app.main.models import *
admin.add_view(ModelView(Laboratory, db.session, category='Labs'))

from app.lab.models import *
admin.add_view(ModelView(LabTest, db.session, category='Tests'))
admin.add_view(ModelView(LabTestOrder, db.session, category='Tests'))
admin.add_view(ModelView(LabTestRecord, db.session, category='Tests'))
admin.add_view(ModelView(LabResultChoiceSet, db.session, category='Tests'))
admin.add_view(ModelView(LabResultChoiceItem, db.session, category='Tests'))
admin.add_view(ModelView(LabActivity, db.session, category='Activities'))
admin.add_view(ModelView(LabCustomer, db.session, category='Customers'))
admin.add_view(ModelView(Announcement, db.session, category='Announcement'))
admin.add_view(ModelView(UserLabAffil, db.session, category='Labs'))


@app.route('/')
def index():
    announcements = Announcement.query.all()
    return render_template('index.html', announcements=announcements)


@app.template_filter('humanizedt')
def humanize_datetime(dt):
    if dt:
        dt = arrow.get(dt)
        return dt.humanize()
    else:
        return ''
