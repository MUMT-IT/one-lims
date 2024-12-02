from app import db
from app.auth.models import User
from sqlalchemy_utils import EmailType


class Laboratory(db.Model):
    __tablename__ = 'labs'
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column('name', db.String(), nullable=False, info={'label': 'Lab Name'})
    desc = db.Column('description', db.Text(), info={'label': 'Description'})
    created_at = db.Column('created_at', db.DateTime(timezone=True))
    active = db.Column('active', db.Boolean(), default=True)
    creator_id = db.Column('creator_id', db.ForeignKey('user.id'))
    creator = db.relationship(User, backref=db.backref('user', lazy=True))
    address = db.Column('address', db.Text(), info={'label': 'Address'})
    email = db.Column('email', EmailType(), info={'label': 'Email'})
    tel = db.Column('tel', db.String(), info={'label': 'Telephone'})
    tax_id = db.Column('tax_id', db.String(), info={'label': 'Tax ID'})
    lat = db.Column('lat', db.Numeric(), info={'label': 'ละติจูด'})
    long = db.Column('long', db.Numeric(), info={'label': 'ลองติจูด'})

    @property
    def num_pending_members(self):
        return len([m for m in self.lab_members if not m.approved])

    @property
    def num_approved_members(self):
        return len([m for m in self.lab_members if m.approved])

    @property
    def pending_test_records(self):
        records = []
        for order in self.test_orders:
            if not order.approved_at:
                records += [r for r in order.active_test_records if r.updated_at is None and not r.reject_record]
        return records

    def __str__(self):
        return self.name


class UserLabAffil(db.Model):
    __tablename__ = 'user_lab_affils'
    user_id = db.Column('user_id', db.ForeignKey('user.id'), primary_key=True)
    lab_id = db.Column('lab_id', db.ForeignKey('labs.id'), primary_key=True)
    joined_at = db.Column('joined_at', db.DateTime(timezone=True))
    approved = db.Column('approved', db.Boolean(), default=False)
    user = db.relationship(User, backref=db.backref('lab_affils',
                                                    lazy=True,
                                                    cascade='all, delete-orphan'))
    lab = db.relationship(Laboratory, backref=db.backref('lab_members',
                                                         cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'user_id': self.user.id,
            'user_firstname': self.user.firstname,
            'user_lastname': self.user.lastname,
            'user_email': self.user.email,
            'user_license_id': self.user.license_id
        }


class Announcement(db.Model):
    __tablename__ = 'announcements'
    user_id = db.Column('user_id', db.ForeignKey('user.id'), primary_key=True)
    category = db.Column('category', db.String(), info={'label': 'Category',
                                                        'choices': [(cat, cat) for cat in ['feature', 'bug', 'news']]})
    detail = db.Column('detail', db.String(), nullable=False)
    added_at = db.Column('added_at', db.DateTime(timezone=True))
    user = db.relationship('User', backref=db.backref('announcements'))
