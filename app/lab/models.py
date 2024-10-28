from datetime import datetime

from sqlalchemy_continuum import make_versioned
import sqlalchemy as sa
from wtforms.validators import Length

from app import db
from app.main.models import Laboratory
from app.auth.models import User

make_versioned(user_cls=None)


class LabCustomer(db.Model):
    __tablename__ = 'lab_customers'
    # id is used as an HN
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    title = db.Column('title', db.String(), info={'label': 'Title',
                                                  'choices': [(t, t) for t in ['นาย',
                                                                               'นาง',
                                                                               'นางสาว',
                                                                               'เด็กหญิง',
                                                                               'เด็กชาย',
                                                                               'พระภิกษุ',
                                                                               'สามเณร']]})
    firstname = db.Column('firstname', db.String(), info={'label': 'First Name'})
    lastname = db.Column('lastname', db.String(), info={'label': 'Last Name'})
    dob = db.Column('dob', db.Date(), info={'label': 'Date of Birth'})
    gender = db.Column('gender', db.String(), info={'label': 'Gender',
                                                    'choices': [(g, g) for g in ['ชาย', 'หญิง']]})
    lab_id = db.Column('lab_id', db.ForeignKey('labs.id'))
    lab = db.relationship(Laboratory, backref=db.backref('customers',
                                                         cascade='all, delete-orphan'))
    tel = db.Column('tel', db.String(), info={'label': 'หมายเลขโทรศัพท์'})
    pid = db.Column('pid', db.String(13), info={'label': 'หมายเลขบัตรประชาชน', 'validators': Length(min=13, max=13)})
    address = db.Column('address', db.Text(), info={'label': 'ที่อยู่'})

    @property
    def fullname(self):
        return '{}{} {}'.format(self.title, self.firstname, self.lastname)

    def __str__(self):
        return self.fullname

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'birthdate': self.dob.strftime('%Y-%m-%d') if self.dob else None,
            'gender': self.gender,
        }

    @property
    def all_test_orders(self):
        return len(self.qual_test_orders) + len(self.quan_test_orders)

    @property
    def pending_test_orders(self):
        return [order for order in self.test_orders if not order.approved_at and not order.cancelled_at]


class LabActivity(db.Model):
    __tablename__ = 'lab_activities'
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    actor_id = db.Column('actor_id', db.ForeignKey('user.id'))
    actor = db.relationship(User, backref=db.backref('activities',
                                                     cascade='all, delete-orphan'))
    message = db.Column('message', db.String(), nullable=False)
    detail = db.Column('detail', db.String())
    added_at = db.Column('added_at', db.DateTime(timezone=True))
    lab_id = db.Column('lab_id', db.ForeignKey('labs.id'))
    lab = db.relationship(Laboratory, backref=db.backref('member_activities',
                                                         cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.actor_id,
            'message': self.message,
            'detail': self.detail,
            'datetime': self.added_at.strftime('%Y-%m-%d %H:%M:%S') if self.added_at else None,
        }


class LabResultChoiceSet(db.Model):
    __tablename__ = 'lab_result_choice_set'
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column('name', db.String())
    lab_id = db.Column('lab_id', db.ForeignKey('labs.id'))
    lab = db.relationship(Laboratory, backref=db.backref('choice_sets',
                                                         cascade='all, delete-orphan'))
    reference = db.Column('reference', db.String())

    def __str__(self):
        return self.name


class LabResultChoiceItem(db.Model):
    __tablename__ = 'lab_result_choice_item'
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    result = db.Column('result', db.String(), nullable=False)
    choice_set_id = db.Column('choices_id', db.ForeignKey('lab_result_choice_set.id'))
    choice_set = db.relationship(LabResultChoiceSet,
                                 backref=db.backref('choice_items',
                                                    cascade='all, delete-orphan'))
    interpretation = db.Column('interpretation', db.String())
    ref = db.Column('ref', db.Boolean(), default=False)

    def __str__(self):
        return self.result


class LabSpecimenContainer(db.Model):
    __tablename__ = 'lab_specimen_containers'
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    container = db.Column('container', db.String(), nullable=False, info={'label': 'Container'})
    max_volume = db.Column('max_volume', db.Numeric(), info={'label': 'Max Volume'})
    lab_id = db.Column('lab_id', db.ForeignKey('labs.id'))
    lab = db.relationship(Laboratory, backref=db.backref('specimen_containers'))

    def __str__(self):
        return self.container


class LabTest(db.Model):
    __versioned__ = {}
    __tablename__ = 'lab_tests'
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column('name', db.String(), nullable=False, info={'label': 'Name'})
    detail = db.Column('detail', db.Text(), info={'label': 'Detail'})
    code = db.Column('code', db.String(), info={'label': 'Code'})
    # for numeric results
    min_value = db.Column('min_value', db.Numeric(), default=0.0, info={'label': 'Min value'})
    max_value = db.Column('max_value', db.Numeric(), info={'label': 'Max value'})
    min_ref_value = db.Column('min_ref_value', db.Numeric(), info={'label': 'Min ref value'})
    max_ref_value = db.Column('max_ref_value', db.Numeric(), info={'label': 'Max ref value'})
    # choices for results in text
    choice_set_id = db.Column('choice_set', db.ForeignKey('lab_result_choice_set.id'))
    choice_set = db.relationship(LabResultChoiceSet)
    active = db.Column('active', db.Boolean(), default=True)
    added_at = db.Column('added_at', db.DateTime(timezone=True))
    lab_id = db.Column('lab_id', db.ForeignKey('labs.id'))
    lab = db.relationship(Laboratory, backref=db.backref('tests',
                                                         cascade='all, delete-orphan'))
    data_type = db.Column('data_type', db.String(), info={'label': 'Data Type',
                                                          'choices': [(c, c) for c in ['Numeric', 'Text']]})
    price = db.Column('price', db.Numeric(), info={'label': 'Price'})
    unit = db.Column('unit', db.String(), info={'label': 'หน่วย'})

    def __str__(self):
        return self.name

    @property
    def reference_values(self):
        return f'[{self.min_ref_value} - {self.max_ref_value} {self.unit}]'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'detail': self.detail,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'min_ref_value': self.min_ref_value,
            'max_ref_value': self.max_ref_value,
            'data_type': self.data_type,
            'active': self.active
        }


class LabSpecimenContainerItem(db.Model):
    __tablename__ = 'lab_specimen_container_items'
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    lab_test_id = db.Column('lab_test_id', db.ForeignKey('lab_tests.id'))
    lab_specimen_container_id = db.Column('lab_specimen_container_id', db.ForeignKey('lab_specimen_containers.id'))
    volume = db.Column('volume', db.Numeric(), info={'label': 'Volume'})
    note = db.Column('note', db.Text())
    test = db.relationship(LabTest, backref=db.backref('specimen_container_items', cascade='all, delete-orphan'))
    specimen_container = db.relationship(LabSpecimenContainer,
                                         backref=db.backref('specimen_container_items', cascade='all, delete-orphan'))
    lab_id = db.Column('lab_id', db.ForeignKey('labs.id'))


class LabOrderCount(db.Model):
    __tablename__ = 'lab_order_counts'
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    year = db.Column('year', db.Integer(), info={'label': 'Year'})
    month = db.Column('month', db.Integer(), info={'label': 'Month'})
    count = db.Column('count', db.Integer(), info={'label': 'Count'})



class LabTestOrder(db.Model):
    __tablename__ = 'lab_test_orders'
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    code = db.Column('code', db.String(), unique=True, nullable=False)
    lab_id = db.Column('lab_id', db.ForeignKey('labs.id'))
    lab = db.relationship(Laboratory, backref=db.backref('test_orders',
                                                         cascade='all, delete-orphan'))
    customer_id = db.Column('customer_id', db.ForeignKey('lab_customers.id'))
    customer = db.relationship(LabCustomer, backref=db.backref('test_orders', cascade='all, delete-orphan'))
    ordered_at = db.Column('ordered_at', db.DateTime(timezone=True))
    ordered_by_id = db.Column('ordered_by_id', db.ForeignKey('user.id'))
    ordered_by = db.relationship(User,
                                 backref=db.backref('quan_test_orders'),
                                 foreign_keys=[ordered_by_id])
    cancelled_at = db.Column('cancelled_at', db.DateTime(timezone=True))
    approved_at = db.Column('approved_at', db.DateTime(timezone=True))
    approver_id = db.Column('approver_id', db.ForeignKey('user.id'))
    approver = db.relationship(User, backref=db.backref('approved_quan_orders'), foreign_keys=[approver_id])

    @property
    def pending_tests(self):
        return len([test for test in self.test_orders if test.finished_at is None])

    @property
    def active_test_records(self):
        return [record for record in self.test_records if record.is_active]

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'order_datetime': self.ordered_at.strftime('%Y-%m-%d %H:%M:%S') if self.ordered_at else None,
            'order_by': self.ordered_by_id,
            'approve_datetime': self.approved_at.strftime('%Y-%m-%d %H:%M:%S') if self.approved_at else None,
            'approver_id': self.approver_id,
        }

    def generate_code(self):
        now = datetime.now()
        order_count = LabOrderCount.query.filter_by(year=now.year, month=now.month).first()
        if not order_count:
            order_count = LabOrderCount(year=now.year, month=now, count=1)
        else:
            order_count.increment()
        db.session.add(order_count)
        db.session.commit()
        self.code = f'{str(order_count.year)[-2:]}{order_count.month:02}{order_count.count:06}'


class LabTestRecord(db.Model):
    __versioned__ = {}
    __tablename__ = 'lab_test_records'
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    num_result = db.Column('num_result', db.Numeric(),
                           info={'label': 'Numeric Result'})
    text_result = db.Column('text_result', db.String(), info={'label': 'Text Result'})
    comment = db.Column('comment', db.Text(), info={'label': 'Comment'})
    updated_at = db.Column('updated_at', db.DateTime(timezone=True))
    cancelled = db.Column('cancelled', db.Boolean(), default=False)
    updater_id = db.Column('updator_id', db.ForeignKey('user.id'))
    updater = db.relationship(User, backref=db.backref('updated_quan_result_records'), foreign_keys=[updater_id])
    test_id = db.Column('test_id', db.ForeignKey('lab_tests.id'))
    test = db.relationship(LabTest, backref=db.backref('test_records', cascade='all, delete-orphan'))
    order_id = db.Column('order_id', db.ForeignKey('lab_test_orders.id'))
    order = db.relationship(LabTestOrder, backref=db.backref('test_records', cascade='all, delete-orphan'))
    reject_record_id = db.Column('reject_record_id', db.ForeignKey('lab_order_reject_records.id'))
    reject_record = db.relationship('LabOrderRejectRecord', backref=db.backref('test_records'))
    received_at = db.Column('received_at', db.DateTime(timezone=True))
    receiver_id = db.Column('receiver_id', db.ForeignKey('user.id'))
    receiver = db.relationship(User,
                               backref=db.backref('received_test_records'),
                               foreign_keys=[receiver_id])

    @property
    def is_active(self):
        return not self.cancelled and \
            not self.reject_record and \
            not self.order.cancelled_at and \
            not self.order.approved_at

    def to_dict(self):
        return {
            'id': self.id,
            'num_result': self.num_result,
            'text_result': self.text_result,
            'reported_datetime': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'reporter_id': self.updater_id,
            'test_id': self.test_id,
            'reject_record_id': self.reject_record_id,
            'receive_datetime': self.received_at.strftime('%Y-%m-%d %H:%M:%S') if self.received_at else None,
            'received_by': self.receiver_id,
            'order_id': self.order_id
        }


class LabOrderRejectRecord(db.Model):
    __tablename__ = 'lab_order_reject_records'
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column('created_at', db.DateTime(timezone=True), nullable=False)
    creator_id = db.Column('creator_id', db.ForeignKey('user.id'))
    reason = db.Column('reason', db.String(), nullable=False, info={'label': 'สาเหตุ',
                                                                    'choices': [(c, c) for c in
                                                                                ['สิ่งส่งตรวจไม่เหมาะสมกับการทดสอบ',
                                                                                 'สิ่งส่งตรวจไม่เพียงพอ',
                                                                                 'คุณภาพของสิ่งส่งตรวจไม่ดี',
                                                                                 'ภาชนะรั่วหรือแตก',
                                                                                 'ไม่มีรายการตรวจ',
                                                                                 'ข้อมูลคนไข้ไม่ตรงกัน', 'อื่นๆ']
                                                                                ]
                                                                    })
    detail = db.Column('detail', db.Text(), info={'label': 'รายละเอียด โปรดระบุ'})

    def to_dict(self):
        return {
            'id': self.id,
            'reject_datetime': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'reason': self.reason,
            'detail': self.detail
        }


sa.orm.configure_mappers()
